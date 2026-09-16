const API_BASE = "http://127.0.0.1:8000";

// --- Recruiter session token helpers --------------------------------
// RecruiterLogin.tsx stores the full /auth/login response (which now
// includes a "token" field) under this sessionStorage key. Every
// recruiter-only call below reads the token from here and sends it as
// "Authorization: Bearer <token>". The two file-download URLs
// (resume, recording) can't send custom headers since they're used
// directly in window.open()/<video src>, so getStoredToken() is
// exported for those call sites to append "?token=..." instead.
const RECRUITER_SESSION_KEY = "ee_recruiter_session";

export function getStoredToken(): string | null {
  const raw = sessionStorage.getItem(RECRUITER_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed.token || null;
  } catch {
    return null;
  }
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// If a recruiter-only call comes back 401, the session is gone or
// expired server-side - clear it locally too and reload, which sends
// the recruiter back to the login screen (RecruiterFlow checks
// sessionStorage on mount).
function handleAuthFailure(res: Response) {
  if (res.status === 401) {
    sessionStorage.removeItem(RECRUITER_SESSION_KEY);
    // A silent reload straight back to the login screen leaves the
    // recruiter with no idea why they were logged out mid-session.
    // This flag is picked up once by RecruiterLogin.tsx to show a
    // proper explanation, then cleared.
    sessionStorage.setItem("ee_recruiter_session_expired", "1");
    window.location.reload();
  }
}

export async function createCandidate(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/candidates/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    console.error("Candidate application failed:", res.status, errorBody);
    throw new Error(`Application failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

export type ParsedResumeFields = {
  full_name: string | null;
  phone: string | null;
  email: string | null;
  current_location: string | null;
  current_organization: string | null;
  current_title: string | null;
};

export async function parseResume(file: File): Promise<ParsedResumeFields> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/candidates/parse-resume`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    // Never block the candidate on a parse failure - just return
    // nothing, so every field falls back to manual entry.
    return {
      full_name: null,
      phone: null,
      email: null,
      current_location: null,
      current_organization: null,
      current_title: null,
    };
  }

  return res.json();
}

export type CompanyChatDisplay =
  | { type: "stat_card"; icon: string; stat: string; caption: string }
  | { type: "icon_list"; icon: string; items: string[] }
  | { type: "step_list"; items: string[] }
  | { type: "info_card"; icon: string; caption: string };

export async function askCompanyChat(
  message: string
): Promise<{ reply: string; link: string | null; display?: CompanyChatDisplay; topic?: string }> {
  const res = await fetch(`${API_BASE}/company-chat/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    if (res.status === 429) {
      return {
        reply: "You've sent a lot of messages quickly - please wait a moment and try again.",
        link: null,
      };
    }
    return {
      reply: "Sorry, I couldn't process that right now. Please try again in a moment.",
      link: null,
    };
  }

  return res.json();
}

export async function getFunFact(): Promise<{ icon: string; stat: string | null; caption: string }> {
  const res = await fetch(`${API_BASE}/company-chat/fun-fact`, {
    method: "POST",
  });

  if (!res.ok) {
    return {
      icon: "\u2139\uFE0F",
      stat: null,
      caption: "Sorry, I couldn't fetch a fact right now - please try again in a moment.",
    };
  }

  return res.json();
}

export async function getCompetencies() {
  const res = await fetch(`${API_BASE}/competencies`);

  if (!res.ok) {
    throw new Error("Failed to load competencies");
  }

  return res.json();
}

export async function generateAssessmentQuestions(payload: {
  candidate_id: string;
  job_id: string;
  role: string;
}) {
  const res = await fetch(`${API_BASE}/assessment/questions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to generate assessment questions");
  }

  return res.json();
}

export async function analyzeAssessment(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/assessment/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to analyze assessment");
  }

  return res.json();
}

export async function getRecruiterDashboard(recruiterSlug?: string, role?: string) {
  const params = new URLSearchParams();
  if (recruiterSlug) params.set("recruiter_slug", recruiterSlug);
  if (role) params.set("role", role);
  const query = params.toString();

  const url = query
    ? `${API_BASE}/dashboard/recruiter?${query}`
    : `${API_BASE}/dashboard/recruiter`;

  const res = await fetch(url, { headers: { ...authHeaders() } });

  if (!res.ok) {
    handleAuthFailure(res);
    throw new Error("Failed to load recruiter dashboard");
  }

  return res.json();
}

export async function shortlistCandidate(candidateId: string) {
  const res = await fetch(`${API_BASE}/scheduling/shortlist/${candidateId}`, {
    method: "POST",
    headers: { ...authHeaders() },
  });

  if (!res.ok) {
    handleAuthFailure(res);
    const errorBody = await res.text();
    throw new Error(`Shortlist failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

export async function getCandidateSlots(candidateId: string, round: "recruiter" | "panel") {
  const res = await fetch(
    `${API_BASE}/scheduling/${candidateId}/slots?round=${round}`
  );

  if (!res.ok) {
    throw new Error("Failed to load slots");
  }

  return res.json();
}

export async function bookSlot(
  candidateId: string,
  slotId: string,
  round: "recruiter" | "panel"
) {
  const res = await fetch(
    `${API_BASE}/scheduling/${candidateId}/book?slot_id=${slotId}&round=${round}`,
    { method: "POST" }
  );

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Booking failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

export async function submitScorecard(
  candidateId: string,
  payload: { shortlist: boolean; recruiter_notes?: string; recruiter_score?: number }
) {
  const res = await fetch(`${API_BASE}/scheduling/${candidateId}/scorecard`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    handleAuthFailure(res);
    const errorBody = await res.text();
    throw new Error(`Scorecard submission failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}
export async function uploadResume(candidateId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/candidates/${candidateId}/resume`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Resume upload failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

export async function rejectCandidate(candidateId: string, reason: string = "") {
  const res = await fetch(
    `${API_BASE}/scheduling/reject/${candidateId}?reason=${encodeURIComponent(reason)}`,
    { method: "POST", headers: { ...authHeaders() } }
  );

  if (!res.ok) {
    handleAuthFailure(res);
    const errorBody = await res.text();
    throw new Error(`Reject failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

export async function saveAssessmentProgress(
  candidateId: string,
  payload: {
    question_id: string;
    competency_key: string;
    mode: string;
    duration_seconds: number;
    tab_switch_count?: number;
    fullscreen_exit_count?: number;
    focus_loss_count?: number;
  }
) {
  const res = await fetch(`${API_BASE}/assessment/progress/${candidateId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to save progress (${res.status})`);
  }

  return res.json();
}

export async function getAssessmentProgress(candidateId: string) {
  const res = await fetch(`${API_BASE}/assessment/progress/${candidateId}`);

  if (!res.ok) {
    throw new Error(`Failed to load progress (${res.status})`);
  }

  return res.json();
}

export async function loginRecruiter(email: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Login failed");
  }

  return res.json();
}

export async function logoutRecruiter(token: string) {
  // Best-effort: invalidates the session server-side too, not just in
  // sessionStorage. Never throws - a failed logout call shouldn't
  // block the person from being logged out locally.
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
  } catch {
    // ignore - network error on logout is not worth surfacing
  }
}

export async function uploadRecording(
  candidateId: string,
  questionId: string,
  mode: string,
  blob: Blob
) {
  const formData = new FormData();
  formData.append("question_id", questionId);
  formData.append("mode", mode);
  formData.append("file", blob, `${questionId}.webm`);

  const res = await fetch(`${API_BASE}/assessment/recording/${candidateId}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Recording upload failed (${res.status})`);
  }

  return res.json();
}

export async function getCandidateRecordings(candidateId: string) {
  const res = await fetch(`${API_BASE}/assessment/recordings/${candidateId}`, {
    headers: { ...authHeaders() },
  });

  if (!res.ok) {
    handleAuthFailure(res);
    throw new Error("Failed to load recordings");
  }

  return res.json();
}

export async function deleteCandidate(candidateId: string) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });

  if (!res.ok) {
    handleAuthFailure(res);
    throw new Error(`Delete failed (${res.status})`);
  }

  return res.json();
}

export async function getRoles() {
  const res = await fetch(`${API_BASE}/roles`);
  if (!res.ok) throw new Error("Failed to load roles");
  return res.json();
}

export async function getRecruiters() {
  const res = await fetch(`${API_BASE}/recruiters`);
  if (!res.ok) throw new Error("Failed to load recruiters");
  return res.json();
}