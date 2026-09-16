import { useState } from "react";
import RecruiterLogin from "./components/RecruiterLogin";
import RecruiterShortlistPage from "./pages/RecruiterShortlistPage";
import SchedulingPage from "./pages/SchedulingPage";
import { logoutRecruiter } from "./api/client";

type RecruiterSession = {
  email: string;
  name: string;
  slug: string;
  token: string;
};

type RecruiterView = "shortlist" | "scheduling";

function BrandMark() {
  return (
    <svg
      className="ee-brand-mark"
      width="26"
      height="26"
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="26" height="26" rx="7" fill="#2E6DA4" />
      <path d="M7 8H10V10.4H8.4V15.6H10V18H7V8Z" fill="white" />
      <rect x="12" y="9.5" width="7" height="1.8" fill="white" />
      <rect x="12" y="14.7" width="7" height="1.8" fill="white" />
    </svg>
  );
}

/**
 * The entire recruiter-facing journey: login gate, then shortlist and
 * scheduling. Completely separate from the candidate flow - no
 * candidate-facing tabs exist here at all.
 */
export default function RecruiterFlow() {
  const [session, setSession] = useState<RecruiterSession | null>(() => {
    const stored = sessionStorage.getItem("ee_recruiter_session");
    return stored ? JSON.parse(stored) : null;
  });
  const [view, setView] = useState<RecruiterView>("shortlist");

  const handleLogout = async () => {
    if (session?.token) {
      await logoutRecruiter(session.token);
    }
    sessionStorage.removeItem("ee_recruiter_session");
    setSession(null);
  };

  if (!session) {
    return (
      <div className="ee-app">
        <nav className="ee-nav">
          <div className="ee-nav-inner">
            <div className="ee-brand">
              <BrandMark />
              EE TalentOS
              <span className="ee-brand-sub">Equal Experts</span>
            </div>
          </div>
        </nav>
        <RecruiterLogin onLoggedIn={setSession} />
      </div>
    );
  }

  return (
    <div className="ee-app">
      <nav className="ee-nav">
        <div className="ee-nav-inner">
          <div className="ee-brand">
            <BrandMark />
            EE TalentOS
            <span className="ee-brand-sub">Equal Experts</span>
          </div>

          <div className="ee-tabs">
            <button
              type="button"
              className={`ee-tab ${view === "shortlist" ? "ee-tab--active" : ""}`}
              onClick={() => setView("shortlist")}
            >
              Shortlist
            </button>
            <button
              type="button"
              className={`ee-tab ${view === "scheduling" ? "ee-tab--active" : ""}`}
              onClick={() => setView("scheduling")}
            >
              Schedule Interview
            </button>
          </div>

          <div className="ee-row" style={{ alignItems: "center", gap: 10 }}>
            <span className="ee-badge ee-badge--brand">Logged in: {session.name}</span>
            <button type="button" className="ee-btn ee-btn--ghost" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </nav>

      {view === "shortlist" && <RecruiterShortlistPage />}
      {view === "scheduling" && <SchedulingPage />}
    </div>
  );
}
