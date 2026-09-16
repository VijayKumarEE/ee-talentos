import { useEffect, useMemo, useState } from "react";
import {
  getRecruiterDashboard,
  shortlistCandidate,
  submitScorecard,
  rejectCandidate,
  getCandidateRecordings,
  deleteCandidate,
  getRoles,
  getRecruiters,
  getStoredToken,
} from "../api/client";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

type RoleOption = { value: string; label: string };
type RecruiterOption = { name: string; slug: string };

type Props = {
  recruiterSlug?: string;
};

type CompetencyResult = {
  key: string;
  label: string;
  score: number;
  level: string;
  evidence: {
    positive: string[];
    gaps: string[];
    risk_flags: string[];
  };
  summary: string;
  follow_up_questions: string[];
  question?: string;
  transcript?: string;
};

type CandidateRow = {
  candidate_id: string;
  full_name: string;
  email: string;
  current_location?: string;
  preferred_location?: string;
  years_of_experience?: number;
  notice_period_days?: number;
  expected_salary?: string;
  fixed_salary?: string;
  variable_pay?: string;
  resume_filename?: string | null;
  resume_original_name?: string | null;
  recruiter_name?: string | null;
  source_channel?: string | null;
  role_applied_for?: string | null;
  tab_switch_count?: number;
  fullscreen_exit_count?: number;
  focus_loss_count?: number;
  stage?: string;
  rejection_reason?: string | null;
  overall_score?: number | null;
  recommendation?: "strong_match" | "review" | "reject" | null;
  top_strengths?: string[];
  competencies?: CompetencyResult[];
  notes?: string | null;
};

type RecordingInfo = {
  question_id: string;
  mode: "audio" | "video";
  duration_seconds: number | null;
  transcript?: string;
  question?: string;
};

const RECOMMENDATION_BADGE: Record<string, string> = {
  strong_match: "ee-badge--success",
  review: "ee-badge--warning",
  reject: "ee-badge--danger",
};

export default function RecruiterShortlistPage({ recruiterSlug: _unused }: Props) {
  const [rows, setRows] = useState<CandidateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");

  // Filters default to "All" so every recruiter sees the full team
  // pipeline by default, matching Greenhouse's unfiltered candidate
  // list - narrowing down is an explicit choice, not tied to login.
  const [roleFilter, setRoleFilter] = useState("");
  const [recruiterFilter, setRecruiterFilter] = useState("");
  const [roleOptions, setRoleOptions] = useState<RoleOption[]>([]);
  const [recruiterOptions, setRecruiterOptions] = useState<RecruiterOption[]>([]);

  const [openScorecardFor, setOpenScorecardFor] = useState<string | null>(null);
  const [scorecardNotes, setScorecardNotes] = useState("");
  const [scorecardScore, setScorecardScore] = useState("");

  const [openRejectFor, setOpenRejectFor] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const [expandedScorecard, setExpandedScorecard] = useState<string | null>(null);
  const [expandedRecordings, setExpandedRecordings] = useState<string | null>(null);
  const [recordingsByCandidate, setRecordingsByCandidate] = useState<Record<string, RecordingInfo[]>>({});
  const [loadingRecordings, setLoadingRecordings] = useState<string | null>(null);

  const [confirmDeleteFor, setConfirmDeleteFor] = useState<string | null>(null);
  const [sentSlotsByCandidate, setSentSlotsByCandidate] = useState<
    Record<string, { label: string; roundLabel: string }[]>
  >({});

  const [busyCandidateId, setBusyCandidateId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<Record<string, string>>({});

  async function load() {
    try {
      setLoading(true);
      const data = await getRecruiterDashboard(recruiterFilter || undefined, roleFilter || undefined);
      setRows(data.candidates || []);
    } catch {
      setMessage("Could not load the recruiter shortlist.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    getRoles().then(setRoleOptions).catch(() => {});
    getRecruiters().then(setRecruiterOptions).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter, recruiterFilter]);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      [row.full_name, row.email, row.current_location, row.preferred_location, row.stage]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q))
    );
  }, [rows, search]);

  const stageBreakdown = useMemo(() => {
    if (rows.length === 0) return "";
    const counts: Record<string, number> = {};
    rows.forEach((row) => {
      const stage = row.stage || "unknown";
      counts[stage] = (counts[stage] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([stage, count]) => `${count} ${stage.replace(/_/g, " ")}`)
      .join(", ");
  }, [rows]);

  const handleShortlist = async (candidateId: string) => {
    setBusyCandidateId(candidateId);
    setActionMessage((prev) => ({ ...prev, [candidateId]: "" }));

    try {
      const result = await shortlistCandidate(candidateId);
      setActionMessage((prev) => ({
        ...prev,
        [candidateId]: "Shortlisted - self-scheduling email sent to the candidate.",
      }));
      setSentSlotsByCandidate((prev) => ({
        ...prev,
        [candidateId]: (result.slots || []).map((s: { label: string }) => ({
          label: s.label,
          roundLabel: "Recruiter Screen",
        })),
      }));
      await load();
    } catch (err) {
      setActionMessage((prev) => ({ ...prev, [candidateId]: "Failed to shortlist candidate." }));
      console.error(err);
    } finally {
      setBusyCandidateId(null);
    }
  };

  const handleOpenReject = (candidateId: string) => {
    setOpenRejectFor(candidateId);
    setRejectReason("");
  };

  const handleConfirmReject = async (candidateId: string) => {
    setBusyCandidateId(candidateId);
    setActionMessage((prev) => ({ ...prev, [candidateId]: "" }));

    try {
      await rejectCandidate(candidateId, rejectReason);
      setActionMessage((prev) => ({
        ...prev,
        [candidateId]: "Candidate rejected - rejection email sent (check backend console).",
      }));
      setOpenRejectFor(null);
      await load();
    } catch (err) {
      setActionMessage((prev) => ({ ...prev, [candidateId]: "Failed to reject candidate." }));
      console.error(err);
    } finally {
      setBusyCandidateId(null);
    }
  };

  const handleOpenScorecard = (candidateId: string) => {
    setOpenScorecardFor(candidateId);
    setScorecardNotes("");
    setScorecardScore("");
  };

  const handleSubmitScorecard = async (candidateId: string, decision: boolean) => {
    setBusyCandidateId(candidateId);
    setActionMessage((prev) => ({ ...prev, [candidateId]: "" }));

    try {
      const result = await submitScorecard(candidateId, {
        shortlist: decision,
        recruiter_notes: scorecardNotes || undefined,
        recruiter_score: scorecardScore ? Number(scorecardScore) : undefined,
      });

      setActionMessage((prev) => ({
        ...prev,
        [candidateId]: decision
          ? "Scorecard saved - panel self-scheduling email sent to the candidate."
          : "Scorecard saved - candidate marked as rejected.",
      }));

      if (decision && result.slots) {
        setSentSlotsByCandidate((prev) => ({
          ...prev,
          [candidateId]: (result.slots || []).map((s: { label: string }) => ({
            label: s.label,
            roundLabel: "Panel Interview",
          })),
        }));
      }

      setOpenScorecardFor(null);
      await load();
    } catch (err) {
      setActionMessage((prev) => ({ ...prev, [candidateId]: "Failed to submit scorecard." }));
      console.error(err);
    } finally {
      setBusyCandidateId(null);
    }
  };

  const handleViewResume = (candidateId: string) => {
    const token = getStoredToken();
    const url =
      API_BASE + "/candidates/" + candidateId + "/resume" +
      (token ? "?token=" + encodeURIComponent(token) : "");
    window.open(url, "_blank");
  };

  const toggleFullScorecard = (candidateId: string) => {
    setExpandedScorecard((prev) => (prev === candidateId ? null : candidateId));
  };

  const toggleRecordings = async (candidateId: string) => {
    if (expandedRecordings === candidateId) {
      setExpandedRecordings(null);
      return;
    }

    setExpandedRecordings(candidateId);

    if (!recordingsByCandidate[candidateId]) {
      setLoadingRecordings(candidateId);
      try {
        const data = await getCandidateRecordings(candidateId);
        setRecordingsByCandidate((prev) => ({ ...prev, [candidateId]: data.recordings || [] }));
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingRecordings(null);
      }
    }
  };

  const handleDeleteCandidate = async (candidateId: string) => {
    setBusyCandidateId(candidateId);

    try {
      await deleteCandidate(candidateId);
      setConfirmDeleteFor(null);
      await load();
    } catch (err) {
      setActionMessage((prev) => ({ ...prev, [candidateId]: "Failed to delete candidate." }));
      console.error(err);
    } finally {
      setBusyCandidateId(null);
    }
  };

  const recordingUrl = (candidateId: string, questionId: string) => {
    const token = getStoredToken();
    return (
      API_BASE + "/assessment/recording/" + candidateId + "/" + questionId +
      (token ? "?token=" + encodeURIComponent(token) : "")
    );
  };

  if (loading) {
    return (
      <div className="ee-page ee-page--wide">
        <div className="ee-empty">Loading recruiter shortlist...</div>
      </div>
    );
  }

  return (
    <div className="ee-page ee-page--wide">
      <div className="ee-page-header">
        <span className="ee-eyebrow">Recruiter workspace</span>
        <h1>Shortlist</h1>
        <p>Review candidates, their AI-generated summary, and move them to the next stage.</p>
      </div>

      <div className="ee-row" style={{ marginBottom: 16, flexWrap: "wrap" }}>
        <div className="ee-field" style={{ marginBottom: 0, minWidth: 220 }}>
          <label className="ee-label">Role</label>
          <select className="ee-select" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="">All roles</option>
            {roleOptions.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>

        <div className="ee-field" style={{ marginBottom: 0, minWidth: 220 }}>
          <label className="ee-label">Recruiter</label>
          <select className="ee-select" value={recruiterFilter} onChange={(e) => setRecruiterFilter(e.target.value)}>
            <option value="">All recruiters</option>
            {recruiterOptions.map((r) => (
              <option key={r.slug} value={r.slug}>{r.name}</option>
            ))}
          </select>
        </div>
      </div>

      {!loading && (
        <p className="ee-muted" style={{ marginBottom: 16 }}>
          {rows.length} candidate{rows.length !== 1 ? "s" : ""}
          {stageBreakdown && ` \u2014 ${stageBreakdown}`}
        </p>
      )}

      <div className="ee-field" style={{ maxWidth: 420 }}>
        <input
          className="ee-input"
          placeholder="Search by name, location, email, or stage"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {message && <p className="ee-muted" style={{ color: "var(--danger)" }}>{message}</p>}

      {filteredRows.length === 0 ? (
        <div className="ee-empty">No candidates yet - once someone applies through your link, they will show up here.</div>
      ) : (
        <div className="ee-stack" style={{ marginTop: 8 }}>
          {filteredRows.map((row) => (
            <div key={row.candidate_id} className="ee-card">
              <div className="ee-row--between">
                <div>
                  <h2>{row.full_name}</h2>
                  <p style={{ marginTop: 4 }}>{row.email}</p>
                  <p style={{ marginTop: 4 }}>
                    {row.current_location || "-"} to {row.preferred_location || "-"}
                  </p>
                  {row.recruiter_name && (
                    <span className="ee-badge ee-badge--neutral" style={{ marginTop: 6, marginRight: 6, display: "inline-block" }}>
                      Recruiter: {row.recruiter_name}
                    </span>
                  )}
                  {row.source_channel && (
                    <span className="ee-badge ee-badge--neutral" style={{ marginTop: 6, display: "inline-block" }}>
                      Source: {row.source_channel}
                    </span>
                  )}
                  {(row.tab_switch_count ?? 0) > 0 && (
                    <span className="ee-badge ee-badge--danger" style={{ marginTop: 6, display: "inline-block" }}>
                      &#9888; {row.tab_switch_count} tab switch{row.tab_switch_count !== 1 ? "es" : ""} during assessment
                    </span>
                  )}
                  {(row.fullscreen_exit_count ?? 0) > 0 && (
                    <span className="ee-badge ee-badge--danger" style={{ marginTop: 6, marginLeft: 6, display: "inline-block" }}>
                      &#9888; {row.fullscreen_exit_count} fullscreen exit{row.fullscreen_exit_count !== 1 ? "s" : ""} during assessment
                    </span>
                  )}
                  {(row.focus_loss_count ?? 0) > 0 && (
                    <span className="ee-badge ee-badge--danger" style={{ marginTop: 6, marginLeft: 6, display: "inline-block" }}>
                      &#9888; {row.focus_loss_count} window focus loss{row.focus_loss_count !== 1 ? "es" : ""} during assessment
                    </span>
                  )}
                </div>

                <div style={{ textAlign: "right" }}>
                  {row.recommendation ? (
                    <span className={`ee-badge ${RECOMMENDATION_BADGE[row.recommendation] || "ee-badge--neutral"}`}>
                      {row.overall_score} / 5 - {row.recommendation.replace("_", " ")}
                    </span>
                  ) : (
                    <span className="ee-badge ee-badge--neutral">Pending assessment</span>
                  )}
                  <div style={{ marginTop: 8 }}>
                    <span className="ee-badge ee-badge--brand">{row.stage ?? "unknown"}</span>
                  </div>
                </div>
              </div>

              <hr className="ee-divider" />

              <div className="ee-row" style={{ gap: 32 }}>
                <div>
                  <div className="ee-label">Experience</div>
                  <div>{row.years_of_experience ?? "-"} years</div>
                </div>
                <div>
                  <div className="ee-label">Notice period</div>
                  <div>{row.notice_period_days ?? "-"} days</div>
                </div>
                <div>
                  <div className="ee-label">Fixed / Variable</div>
                  <div>{row.fixed_salary ?? "-"} / {row.variable_pay ?? "-"}</div>
                </div>
              </div>

              <div className="ee-row" style={{ marginTop: 12, flexWrap: "wrap" }}>
                {row.resume_filename && (
                  <button
                    type="button"
                    className="ee-badge ee-badge--brand"
                    style={{ border: "none", cursor: "pointer" }}
                    onClick={() => handleViewResume(row.candidate_id)}
                  >
                    View Resume
                  </button>
                )}

                {row.competencies && row.competencies.length > 0 && (
                  <button
                    type="button"
                    className="ee-badge ee-badge--brand"
                    style={{ border: "none", cursor: "pointer" }}
                    onClick={() => toggleFullScorecard(row.candidate_id)}
                  >
                    {expandedScorecard === row.candidate_id ? "Hide" : "View"} full AI scorecard
                  </button>
                )}

                <button
                  type="button"
                  className="ee-badge ee-badge--brand"
                  style={{ border: "none", cursor: "pointer" }}
                  onClick={() => toggleRecordings(row.candidate_id)}
                >
                  {expandedRecordings === row.candidate_id ? "Hide" : "View"} recordings
                </button>
              </div>

              {expandedScorecard === row.candidate_id && row.competencies && (
                <div className="ee-stack" style={{ marginTop: 16 }}>
                  {row.competencies.map((item) => (
                    <div key={item.key} className="ee-card ee-card--highlight">
                      <div className="ee-row--between">
                        <h3>{item.label}</h3>
                        <span className="ee-badge ee-badge--brand">{item.score} / 5 - {item.level}</span>
                      </div>

                      {item.question && (
                        <>
                          <div className="ee-label" style={{ marginTop: 12 }}>Question asked</div>
                          <p style={{ marginTop: 4, fontWeight: 500 }}>{item.question}</p>
                        </>
                      )}

                      <div className="ee-label" style={{ marginTop: 12 }}>Candidate's answer</div>
                      {item.transcript ? (
                        <p style={{ marginTop: 4 }}>{item.transcript}</p>
                      ) : (
                        <p className="ee-muted" style={{ marginTop: 4 }}>No transcript available for this answer.</p>
                      )}

                      {item.evidence.positive.length > 0 && (
                        <>
                          <div className="ee-label" style={{ marginTop: 12 }}>Positive evidence</div>
                          <ul className="ee-list-plain">
                            {item.evidence.positive.map((line, i) => <li key={i}>{line}</li>)}
                          </ul>
                        </>
                      )}

                      {item.evidence.gaps.length > 0 && (
                        <>
                          <div className="ee-label" style={{ marginTop: 12 }}>Gaps</div>
                          <ul className="ee-list-plain">
                            {item.evidence.gaps.map((line, i) => <li key={i}>{line}</li>)}
                          </ul>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {expandedRecordings === row.candidate_id && (
                <div className="ee-card ee-card--highlight" style={{ marginTop: 16 }}>
                  <h3 style={{ marginBottom: 14 }}>Recordings</h3>

                  {loadingRecordings === row.candidate_id && <p className="ee-muted">Loading...</p>}

                  {loadingRecordings !== row.candidate_id && (
                    (recordingsByCandidate[row.candidate_id] || []).length === 0 ? (
                      <p className="ee-muted">No recordings saved for this candidate yet.</p>
                    ) : (
                      <div className="ee-stack">
                        {(recordingsByCandidate[row.candidate_id] || []).map((rec) => (
                          <div key={rec.question_id} className="ee-card">
                            <div className="ee-label" style={{ marginBottom: 6 }}>
                              {rec.question_id} - {rec.mode}
                            </div>

                            {rec.question && (
                              <p style={{ fontWeight: 500, marginBottom: 10 }}>{rec.question}</p>
                            )}

                            {rec.mode === "video" ? (
                              <video
                                controls
                                style={{ width: "100%", maxWidth: 360, borderRadius: 8 }}
                                src={recordingUrl(row.candidate_id, rec.question_id)}
                              />
                            ) : (
                              <audio
                                controls
                                style={{ width: "100%" }}
                                src={recordingUrl(row.candidate_id, rec.question_id)}
                              />
                            )}

                            <div className="ee-label" style={{ marginTop: 10 }}>Transcript</div>
                            {rec.transcript ? (
                              <p style={{ marginTop: 4 }}>{rec.transcript}</p>
                            ) : (
                              <p className="ee-muted" style={{ marginTop: 4 }}>
                                No transcript available (transcription may have failed, or ffmpeg/model isn't set up on this machine yet).
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )
                  )}
                </div>
              )}

              {row.notes && (
                <>
                  <div className="ee-label" style={{ marginTop: 16 }}>Assessment notes</div>
                  <p style={{ marginTop: 4 }}>{row.notes}</p>
                </>
              )}

              {row.rejection_reason && (
                <>
                  <div className="ee-label" style={{ marginTop: 16 }}>Rejection reason</div>
                  <p style={{ marginTop: 4 }}>{row.rejection_reason}</p>
                </>
              )}

              {(() => {
                const canShortlist = row.stage === "assessed";
                const canSubmitScorecard = row.stage === "recruiter_scheduling_sent";
                const noActionYet = !canShortlist && !canSubmitScorecard;
                const waitingLabel =
                  row.stage === "applied" || row.stage === "assessment_in_progress"
                    ? "Waiting on the candidate to complete their assessment."
                    : row.stage === "auto_rejected_experience"
                    ? "Auto-rejected below the experience bar - no action needed."
                    : row.stage === "panel_scheduling_sent"
                    ? "Advanced - panel interview scheduling sent."
                    : row.stage === "rejected"
                    ? "Rejected - no further action needed."
                    : null;

                return (
                  <div className="ee-row" style={{ marginTop: 20, alignItems: "center" }}>
                    {canShortlist && (
                      <>
                        <button
                          type="button"
                          className="ee-btn ee-btn--primary"
                          disabled={busyCandidateId === row.candidate_id}
                          onClick={() => handleShortlist(row.candidate_id)}
                        >
                          {busyCandidateId === row.candidate_id ? "Working..." : "Shortlist"}
                        </button>
                        <button
                          type="button"
                          className="ee-btn ee-btn--danger-outline"
                          disabled={busyCandidateId === row.candidate_id}
                          onClick={() => handleOpenReject(row.candidate_id)}
                        >
                          Reject
                        </button>
                      </>
                    )}

                    {canSubmitScorecard && (
                      <button
                        type="button"
                        className="ee-btn ee-btn--outline"
                        disabled={busyCandidateId === row.candidate_id}
                        onClick={() => handleOpenScorecard(row.candidate_id)}
                      >
                        Submit scorecard
                      </button>
                    )}

                    {noActionYet && waitingLabel && (
                      <span className="ee-muted" style={{ fontSize: 13.5 }}>{waitingLabel}</span>
                    )}

                    <button
                      type="button"
                      className="ee-btn ee-btn--ghost"
                      disabled={busyCandidateId === row.candidate_id}
                      onClick={() => setConfirmDeleteFor(row.candidate_id)}
                      style={{ marginLeft: "auto", color: "var(--danger)" }}
                    >
                      Delete
                    </button>
                  </div>
                );
              })()}

              {confirmDeleteFor === row.candidate_id && (
                <div className="ee-card ee-card--highlight" style={{ marginTop: 16 }}>
                  <h3 style={{ marginBottom: 10 }}>Delete this candidate?</h3>
                  <p className="ee-muted" style={{ marginBottom: 14 }}>
                    This permanently removes {row.full_name}'s application, assessment, resume,
                    and any recordings. This can't be undone - use this to clear out test data
                    before a real demo.
                  </p>
                  <div className="ee-row">
                    <button
                      type="button"
                      className="ee-btn ee-btn--danger-outline"
                      disabled={busyCandidateId === row.candidate_id}
                      onClick={() => handleDeleteCandidate(row.candidate_id)}
                    >
                      {busyCandidateId === row.candidate_id ? "Deleting..." : "Yes, delete permanently"}
                    </button>
                    <button type="button" className="ee-btn ee-btn--ghost" onClick={() => setConfirmDeleteFor(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {openRejectFor === row.candidate_id && (
                <div className="ee-card ee-card--highlight" style={{ marginTop: 16 }}>
                  <h3 style={{ marginBottom: 14 }}>Reject candidate</h3>

                  <div className="ee-field">
                    <label className="ee-label">Reason (included in the rejection email)</label>
                    <textarea
                      className="ee-textarea"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      rows={3}
                      placeholder="e.g. We're moving forward with candidates whose experience more closely matches..."
                    />
                  </div>

                  <div className="ee-row">
                    <button
                      type="button"
                      className="ee-btn ee-btn--danger-outline"
                      disabled={busyCandidateId === row.candidate_id}
                      onClick={() => handleConfirmReject(row.candidate_id)}
                    >
                      Confirm reject
                    </button>
                    <button type="button" className="ee-btn ee-btn--ghost" onClick={() => setOpenRejectFor(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {openScorecardFor === row.candidate_id && (
                <div className="ee-card ee-card--highlight" style={{ marginTop: 16 }}>
                  <h3 style={{ marginBottom: 14 }}>Scorecard</h3>

                  <div className="ee-field">
                    <label className="ee-label">Recruiter notes</label>
                    <textarea
                      className="ee-textarea"
                      value={scorecardNotes}
                      onChange={(e) => setScorecardNotes(e.target.value)}
                      rows={3}
                    />
                  </div>

                  <div className="ee-field">
                    <label className="ee-label">Recruiter score (0-5)</label>
                    <input
                      className="ee-input"
                      value={scorecardScore}
                      onChange={(e) => setScorecardScore(e.target.value)}
                    />
                  </div>

                  <div className="ee-row">
                    <button
                      type="button"
                      className="ee-btn ee-btn--primary"
                      disabled={busyCandidateId === row.candidate_id}
                      onClick={() => handleSubmitScorecard(row.candidate_id, true)}
                    >
                      Yes - advance to panel
                    </button>
                    <button
                      type="button"
                      className="ee-btn ee-btn--danger-outline"
                      disabled={busyCandidateId === row.candidate_id}
                      onClick={() => handleSubmitScorecard(row.candidate_id, false)}
                    >
                      No - reject
                    </button>
                    <button type="button" className="ee-btn ee-btn--ghost" onClick={() => setOpenScorecardFor(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {sentSlotsByCandidate[row.candidate_id] && sentSlotsByCandidate[row.candidate_id].length > 0 && (
                <div className="ee-card ee-card--success" style={{ marginTop: 12 }}>
                  <div className="ee-label" style={{ marginBottom: 8 }}>
                    Email sent to {row.full_name} - {sentSlotsByCandidate[row.candidate_id][0].roundLabel} times offered
                  </div>
                  <div className="ee-row" style={{ flexWrap: "wrap" }}>
                    {sentSlotsByCandidate[row.candidate_id].slice(0, 8).map((slot, i) => (
                      <span key={i} className="ee-badge ee-badge--neutral">{slot.label}</span>
                    ))}
                  </div>
                  <p className="ee-muted" style={{ marginTop: 8, fontSize: 13 }}>
                    The candidate can pick any of these from the "Schedule Interview" page using their Candidate ID.
                  </p>
                </div>
              )}

              {actionMessage[row.candidate_id] && (
                <p className="ee-muted" style={{ marginTop: 12, color: "var(--success)" }}>
                  {actionMessage[row.candidate_id]}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
