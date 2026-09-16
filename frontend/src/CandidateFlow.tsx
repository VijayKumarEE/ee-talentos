import { useState } from "react";
import { useParams } from "react-router-dom";
import CandidateForm from "./components/CandidateForm";
import AssessmentPage from "./pages/AssessmentPage";
import CompanyChatWidget from "./components/CompanyChatWidget";

/**
 * The entire candidate-facing journey: apply, then assess, then done.
 * Deliberately has NO nav bar and NO way to jump to any recruiter-side
 * screen - once a candidate lands here, this is the whole experience,
 * and it ends cleanly after they submit their assessment.
 */
export default function CandidateFlow() {
  const { code } = useParams<{ code?: string }>();
  const [candidateId, setCandidateId] = useState<string>("");
  const [step, setStep] = useState<"apply" | "assessment">("apply");

  return (
    <div className="ee-app">
      <div className="ee-nav">
        <div className="ee-nav-inner" style={{ justifyContent: "center" }}>
          <div className="ee-brand">
            <span className="ee-brand-mark" style={{ display: "inline-flex" }}>
              <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="26" height="26" rx="7" fill="#2E6DA4" />
                <path d="M7 8H10V10.4H8.4V15.6H10V18H7V8Z" fill="white" />
                <rect x="12" y="9.5" width="7" height="1.8" fill="white" />
                <rect x="12" y="14.7" width="7" height="1.8" fill="white" />
              </svg>
            </span>
            EE TalentOS
            <span className="ee-brand-sub">Equal Experts</span>
          </div>
        </div>
      </div>

      {step === "apply" && (
        <>
          <CandidateForm
            recruiterSlug={code || null}
            onSubmitted={(id) => {
              setCandidateId(id);
              setStep("assessment");
            }}
          />
          <CompanyChatWidget />
        </>
      )}

      {step === "assessment" && <AssessmentPage candidateId={candidateId} />}
    </div>
  );
}
