import { useEffect, useState } from "react";
import { loginRecruiter } from "../api/client";

type Props = {
  onLoggedIn: (recruiter: { email: string; name: string; slug: string; token: string }) => void;
};

export default function RecruiterLogin({ onLoggedIn }: Props) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem("ee_recruiter_session_expired")) {
      sessionStorage.removeItem("ee_recruiter_session_expired");
      setError("Your session expired or you were logged out. Please log in again.");
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const recruiter = await loginRecruiter(email.trim());
      sessionStorage.setItem("ee_recruiter_session", JSON.stringify(recruiter));
      onLoggedIn(recruiter);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ee-page">
      <div className="ee-page-header">
        <span className="ee-eyebrow">Recruiter access</span>
        <h1>Log in to continue</h1>
        <p>Enter your Equal Experts email to access candidate shortlists and scorecards.</p>
      </div>

      <div className="ee-card" style={{ maxWidth: 420 }}>
        <form onSubmit={handleSubmit}>
          <div className="ee-field">
            <label className="ee-label">Work email</label>
            <input
              className="ee-input"
              type="email"
              placeholder="you@equalexperts.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <button type="submit" className="ee-btn ee-btn--primary ee-btn--block" disabled={loading || !email}>
            {loading ? "Checking..." : "Log in"}
          </button>
        </form>

        {error && <p className="ee-muted" style={{ color: "var(--danger)", marginTop: 12 }}>{error}</p>}
      </div>
    </div>
  );
}
