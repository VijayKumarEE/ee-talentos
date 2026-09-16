import { useState } from "react";
import { createCandidate, uploadResume, parseResume } from "../api/client";

const GENERIC_SUBMIT_ERROR = "Something went wrong while submitting the application.";

// client.ts throws errors shaped like:
// "Application failed (422): {"detail":[{"type":"value_error","loc":["body","email"],"msg":"..."}]}"
// A bare catch{} was previously discarding this entirely and always
// showing GENERIC_SUBMIT_ERROR, even for something as simple and
// fixable as a malformed email address. This pulls the actual
// FastAPI validation message back out so the candidate can fix the
// real problem instead of hitting a dead end.
function extractSubmitErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return GENERIC_SUBMIT_ERROR;

  const jsonStart = err.message.indexOf("{");
  if (jsonStart < 0) return GENERIC_SUBMIT_ERROR;

  try {
    const parsed = JSON.parse(err.message.slice(jsonStart));
    const detail = parsed?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      const loc = Array.isArray(first?.loc) ? first.loc : [];
      const field = loc.length > 0 ? loc[loc.length - 1] : null;
      const msg = typeof first?.msg === "string" ? first.msg : null;

      if (msg) {
        return typeof field === "string"
          ? `Please check the "${field}" field: ${msg}`
          : msg;
      }
    }
  } catch {
    // Not JSON - e.g. a network failure or an unexpected error page -
    // fall through to the generic message below.
  }

  return GENERIC_SUBMIT_ERROR;
}

type Props = {
  onSubmitted: (candidateId: string) => void;
  recruiterSlug?: string | null;
};

export default function CandidateForm({ onSubmitted, recruiterSlug }: Props) {
  const [form, setForm] = useState({
    job_id: "devops-senior-001",
    role_applied_for: "operability-engineer",
    full_name: "",
    email: "",
    phone: "",
    current_location: "",
    preferred_location: "",
    years_of_experience: "",
    months_of_experience: "",
    current_organization: "",
    current_role: "",
    interviewed_last_6_months: "no",
    notice_period_days: "",
    expected_salary: "",
    current_salary: "",
    fixed_salary: "",
    variable_pay: "",
    call_mode: "google_meet",
    source_channel: "",
  });

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [parsingResume, setParsingResume] = useState(false);
  const [autoFilledFields, setAutoFilledFields] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [autoRejected, setAutoRejected] = useState(false);

  const updateField = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleResumeChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;

    if (file) {
      const ext = file.name.toLowerCase().split(".").pop();
      if (!["pdf", "doc", "docx"].includes(ext || "")) {
        setMessage("Please upload a PDF, DOC, or DOCX file.");
        e.target.value = "";
        setResumeFile(null);
        return;
      }
    }

    setResumeFile(file);
    setMessage("");
    setAutoFilledFields([]);

    if (!file) return;

    // .doc (legacy Word format) can't be parsed - skip straight to
    // manual entry rather than showing a spinner for a call that will
    // always come back empty.
    const ext = file.name.toLowerCase().split(".").pop();
    if (ext === "doc") return;

    setParsingResume(true);
    try {
      const fields = await parseResume(file);
      const filled: string[] = [];

      setForm((prev) => {
        const next = { ...prev };
        if (fields.full_name) {
          next.full_name = fields.full_name;
          filled.push("full_name");
        }
        if (fields.email) {
          next.email = fields.email;
          filled.push("email");
        }
        if (fields.phone) {
          next.phone = fields.phone;
          filled.push("phone");
        }
        if (fields.current_location) {
          next.current_location = fields.current_location;
          filled.push("current_location");
        }
        if (fields.current_organization) {
          next.current_organization = fields.current_organization;
          filled.push("current_organization");
        }
        if (fields.current_title) {
          next.current_role = fields.current_title;
          filled.push("current_role");
        }
        return next;
      });

      setAutoFilledFields(filled);
    } catch (err) {
      // Parsing failing entirely just means manual entry, same as
      // before this feature existed - never blocks the candidate.
      console.error("Resume parsing failed:", err);
    } finally {
      setParsingResume(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    setMessage("");

    try {
      const payload = {
        ...form,
        years_of_experience: form.years_of_experience
          ? Number(form.years_of_experience)
          : null,
        months_of_experience: form.months_of_experience
          ? Number(form.months_of_experience)
          : null,
        notice_period_days: form.notice_period_days
          ? Number(form.notice_period_days)
          : null,
        interviewed_last_6_months: form.interviewed_last_6_months === "yes",
        recruiter_slug: recruiterSlug || null,
      };

      const result = await createCandidate(payload);
      const candidateId = result.candidate_id as string;

      if (resumeFile) {
        try {
          await uploadResume(candidateId, resumeFile);
        } catch (uploadErr) {
          console.error(uploadErr);
          setMessage(
            "Application submitted, but the resume upload failed. You can try again later."
          );
        }
      }

      if (result.auto_rejected) {
        // Below the minimum experience bar - stop here with a generic
        // thank-you rather than proceeding to the assessment. The
        // specific reason is deliberately not shown to the candidate.
        setAutoRejected(true);
      } else {
        onSubmitted(candidateId);
      }
    } catch (err) {
      setMessage(extractSubmitErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (autoRejected) {
    return (
      <div className="ee-page">
        <div className="ee-card">
          <h1>Thank you for applying</h1>
          <p className="ee-muted" style={{ marginTop: 12 }}>
            Thanks for taking the time to apply. We've received your application and our
            team will be in touch if there's a role that's a good fit.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="ee-page">
      <div className="ee-page-header">
        <span className="ee-eyebrow">Candidate application</span>
        <h1>Apply for a role</h1>
        <p>Tell us about yourself, then complete a short pre-screening assessment.</p>
        <p><strong>The whole assessment should not take more than 5-7 minutes.</strong></p>
      </div>

      <div className="ee-card">
        <form onSubmit={handleSubmit}>
          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Role you're applying for</label>
              <select className="ee-select" value={form.role_applied_for} onChange={(e) => updateField("role_applied_for", e.target.value)}>
                <option value="operability-engineer">Operability Engineer (DevOps)</option>
                <option value="backend-engineer">Backend Engineer</option>
                <option value="genai-engineer">Gen AI Engineer</option>
                <option value="frontend-engineer">Front End Engineer</option>
                <option value="qa-engineer">QA Engineer</option>
                <option value="data-engineer">Data Engineer</option>
                <option value="business-analyst">Business Analyst</option>
                <option value="delivery-lead">Delivery Lead</option>
                <option value="mobile-android">Mobile Developer - Android</option>
                <option value="mobile-ios">Mobile Developer - iOS</option>
              </select>
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">How did you hear about this role?</label>
              <select className="ee-select" value={form.source_channel} onChange={(e) => updateField("source_channel", e.target.value)}>
                <option value="">Select an option</option>
                <option value="linkedin">LinkedIn</option>
                <option value="naukri">Naukri</option>
                <option value="referral">Referral</option>
                <option value="company_website">Company Website</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div className="ee-field" style={{ maxWidth: 460 }}>
            <label className="ee-label">Resume (PDF, DOC, or DOCX)</label>
            <input
              className="ee-input"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleResumeChange}
            />
            {resumeFile && (
              <span className="ee-muted" style={{ fontSize: 13 }}>
                Selected: {resumeFile.name}
              </span>
            )}
            {parsingResume && (
              <p className="ee-muted" style={{ fontSize: 13, marginTop: 6 }}>
                Reading your resume to fill in the fields below...
              </p>
            )}
            {!parsingResume && autoFilledFields.length > 0 && (
              <p className="ee-muted" style={{ fontSize: 13, marginTop: 6 }}>
                We've filled in a few fields from your resume - please check they're
                correct and fill in anything we missed.
              </p>
            )}
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Full name <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="ee-input" required placeholder="Jane Doe" value={form.full_name} onChange={(e) => updateField("full_name", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Email <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="ee-input" required type="email" placeholder="jane@example.com" value={form.email} onChange={(e) => updateField("email", e.target.value)} />
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Phone</label>
              <input className="ee-input" placeholder="+1 555 000 0000" value={form.phone} onChange={(e) => updateField("phone", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Current organization</label>
              <input className="ee-input" placeholder="Acme Corp" value={form.current_organization} onChange={(e) => updateField("current_organization", e.target.value)} />
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Current location <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="ee-input" required placeholder="City, Country" value={form.current_location} onChange={(e) => updateField("current_location", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Preferred location</label>
              <select className="ee-select" value={form.preferred_location} onChange={(e) => updateField("preferred_location", e.target.value)}>
                <option value="">Select a location</option>
                <option value="Pune">Pune</option>
                <option value="Bangalore">Bangalore</option>
                <option value="Chennai">Chennai</option>
                <option value="Gurgaon">Gurgaon</option>
              </select>
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 110 }}>
              <label className="ee-label">Years of experience</label>
              <input className="ee-input" placeholder="5" value={form.years_of_experience} onChange={(e) => updateField("years_of_experience", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 110 }}>
              <label className="ee-label">Months</label>
              <input className="ee-input" placeholder="6" value={form.months_of_experience} onChange={(e) => updateField("months_of_experience", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 2, minWidth: 200 }}>
              <label className="ee-label">Current role</label>
              <input className="ee-input" placeholder="Senior DevOps Engineer" value={form.current_role} onChange={(e) => updateField("current_role", e.target.value)} />
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 200 }}>
              <label className="ee-label">Have you interviewed at Equal Experts in the last 6 months?</label>
              <select className="ee-select" value={form.interviewed_last_6_months} onChange={(e) => updateField("interviewed_last_6_months", e.target.value)}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 160 }}>
              <label className="ee-label">Notice period (days) <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="ee-input" required placeholder="30" value={form.notice_period_days} onChange={(e) => updateField("notice_period_days", e.target.value)} />
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 160 }}>
              <label className="ee-label">Current salary (CTC) <span style={{ color: "var(--danger)" }}>*</span></label>
              <input className="ee-input" required placeholder="16 LPA" value={form.current_salary} onChange={(e) => updateField("current_salary", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 160 }}>
              <label className="ee-label">Expected salary (CTC)</label>
              <input className="ee-input" placeholder="20 LPA" value={form.expected_salary} onChange={(e) => updateField("expected_salary", e.target.value)} />
            </div>
          </div>

          <div className="ee-row">
            <div className="ee-field" style={{ flex: 1, minWidth: 160 }}>
              <label className="ee-label">Fixed salary (current)</label>
              <input className="ee-input" placeholder="12 LPA" value={form.fixed_salary} onChange={(e) => updateField("fixed_salary", e.target.value)} />
            </div>
            <div className="ee-field" style={{ flex: 1, minWidth: 160 }}>
              <label className="ee-label">Variable pay (current)</label>
              <input className="ee-input" placeholder="4 LPA" value={form.variable_pay} onChange={(e) => updateField("variable_pay", e.target.value)} />
            </div>
          </div>

          <div className="ee-field">
            <label className="ee-label">Call mode for the recruiter call</label>
            <select className="ee-select" style={{ maxWidth: 320 }} value={form.call_mode} onChange={(e) => updateField("call_mode", e.target.value)}>
              <option value="google_meet">Google Meet (video call)</option>
              <option value="zoom">Zoom (video call)</option>
            </select>
            <p className="ee-muted" style={{ fontSize: 13, marginTop: 6 }}>
              Once a recruiter shortlists you, you'll get an email to pick a time from their real calendar availability.
            </p>
          </div>

          <button type="submit" className="ee-btn ee-btn--primary ee-btn--block" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? "Submitting..." : "Submit application"}
          </button>
        </form>

        {message && <p className="ee-muted" style={{ marginTop: 16 }}>{message}</p>}
      </div>
    </div>
  );
}
