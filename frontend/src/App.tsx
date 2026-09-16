import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import CandidateFlow from "./CandidateFlow";
import RecruiterFlow from "./RecruiterFlow";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/apply" element={<CandidateFlow />} />
        <Route path="/apply/:code" element={<CandidateFlow />} />
        <Route path="/recruiter" element={<RecruiterFlow />} />
        <Route path="/" element={<Navigate to="/apply" replace />} />
        <Route path="*" element={<Navigate to="/apply" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
