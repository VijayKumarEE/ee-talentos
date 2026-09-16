import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import CandidateFlow from "./CandidateFlow";
import RecruiterFlow from "./RecruiterFlow";

// HashRouter (not BrowserRouter) so this works unmodified on GitHub
// Pages: GH Pages serves static files with no server-side rewrite, so
// a real BrowserRouter route like /recruiter would 404 on a hard
// refresh or a shared link (GH Pages has no server to redirect
// unknown paths back to index.html). With HashRouter, everything after
// the "#" (e.g. #/recruiter) never leaves the browser, so index.html
// is always what loads, refresh or not - at the cost of URLs looking
// like ".../#/apply" instead of ".../apply". This one line is what
// keeps "no broken routes when the recruiter refreshes the page"
// (handover brief, section 31) true without needing a build-time base
// path or a 404.html redirect hack, and it behaves identically in
// local dev too.
export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/apply" element={<CandidateFlow />} />
        <Route path="/apply/:code" element={<CandidateFlow />} />
        <Route path="/recruiter" element={<RecruiterFlow />} />
        <Route path="/" element={<Navigate to="/apply" replace />} />
        <Route path="*" element={<Navigate to="/apply" replace />} />
      </Routes>
    </HashRouter>
  );
}
