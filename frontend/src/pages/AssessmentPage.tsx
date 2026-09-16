import { useEffect, useRef, useState } from "react";
import {
  analyzeAssessment,
  generateAssessmentQuestions,
  saveAssessmentProgress,
  getAssessmentProgress,
  uploadRecording,
} from "../api/client";

type Props = {
  candidateId: string;
};

type AssessmentQuestion = {
  question_id: string;
  competency_key: string;
  question: string;
};

type AssessmentQuestionsResponse = {
  candidate_id: string;
  job_id: string;
  role: string;
  questions: AssessmentQuestion[];
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
};

type AssessmentResponse = {
  candidate_id: string;
  job_id: string;
  role: string;
  stage: string;
  competencies: CompetencyResult[];
  overall_score: number;
  recommendation: "strong_match" | "review" | "reject";
  notes: string;
  metadata: Record<string, unknown>;
};

type ResponseMode = "audio" | "video";

type Recording = {
  mode: ResponseMode;
  blobUrl: string | null; // null when restored from saved progress (no local file)
  blob: Blob | null; // the actual recording, uploaded on Save & Continue
  durationSeconds: number;
  savedRemotely: boolean;
};

export default function AssessmentPage({ candidateId }: Props) {
  const [jobId] = useState("devops-senior-001");
  const [role, setRole] = useState("the role");

  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [recordings, setRecordings] = useState<Record<string, Recording>>({});

  const [result, setResult] = useState<AssessmentResponse | null>(null);

  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [savingProgress, setSavingProgress] = useState(false);

  const [message, setMessage] = useState("");
  const [started, setStarted] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Recording-in-progress state
  const [recordingMode, setRecordingMode] = useState<ResponseMode | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [recordingError, setRecordingError] = useState<string>("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const videoPreviewRef = useRef<HTMLVideoElement | null>(null);
  const elapsedSecondsRef = useRef(0);

  // Proctoring: tracks tab/window switches for the whole assessment.
  // isRecordingRef mirrors recordingMode so the visibilitychange
  // listener (registered once) always reads the latest recording
  // state, avoiding React's stale-closure trap with global listeners.
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const tabSwitchCountRef = useRef(0);
  const isRecordingRef = useRef(false);
  const discardRecordingRef = useRef(false);

  // Proctoring: fullscreen enforcement while recording. Kept as a
  // second, separate counter from tab-switches (not merged into one
  // number) so a recruiter can tell "left the tab" apart from "exited
  // fullscreen." fullscreenActiveRef is only true when THIS take
  // successfully entered fullscreen - some browsers (notably iPhone
  // Safari, which has no Fullscreen API for anything but a <video>
  // element) will silently fail to enter fullscreen, and in that case
  // we don't want to penalize the candidate for something their
  // browser never actually enforced. intentionalFullscreenExitRef
  // guards against the race where clicking "Stop Recording" exits
  // fullscreen programmatically - that exit fires the same
  // fullscreenchange event as a candidate-initiated Esc-key exit, so
  // without this flag a normal stop would look identical to a
  // violation.
  const [fullscreenExitCount, setFullscreenExitCount] = useState(0);
  const fullscreenExitCountRef = useRef(0);
  const fullscreenActiveRef = useRef(false);
  const intentionalFullscreenExitRef = useRef(false);
  const fullscreenSupported =
    typeof document !== "undefined" &&
    document.fullscreenEnabled &&
    typeof document.documentElement.requestFullscreen === "function";

  // Proctoring: OS-level window focus loss (Alt-Tab/Cmd-Tab to a
  // different application). This is a third, independent signal from
  // tab-switch and fullscreen-exit - it exists specifically because
  // fullscreen enforcement doesn't work at all on iPhone Safari, and
  // switching to a different app doesn't always flip
  // document.hidden (visibilitychange) the way switching browser
  // tabs does. A plain `window.blur` event, by contrast, fires
  // whenever this window loses OS focus for any reason, on every
  // device - so it closes the gap the other two checks can leave on
  // a phone. Some overlap with the other two counters incrementing
  // together for the same real action (e.g. a normal tab-switch)
  // is expected and fine - it's still accurate, not double-counted
  // noise.
  const [focusLossCount, setFocusLossCount] = useState(0);
  const focusLossCountRef = useRef(0);

  useEffect(() => {
    async function loadQuestionsAndProgress() {
      try {
        setLoadingQuestions(true);
        setMessage("");

        const data: AssessmentQuestionsResponse =
          await generateAssessmentQuestions({
            candidate_id: candidateId,
            job_id: jobId,
            role,
          });

        setQuestions(data.questions);
        setRole(data.role);

        // Resume: pull any previously saved progress and mark those
        // questions as already answered.
        try {
          const progressData = await getAssessmentProgress(candidateId);
          const savedProgress = progressData.progress || {};

          const restored: Record<string, Recording> = {};
          Object.entries(savedProgress).forEach(([questionId, value]) => {
            const v = value as { mode: ResponseMode; duration_seconds: number };
            restored[questionId] = {
              mode: v.mode,
              blobUrl: null,
              blob: null,
              durationSeconds: v.duration_seconds,
              savedRemotely: true,
            };
          });

          if (Object.keys(restored).length > 0) {
            setRecordings(restored);

            // Jump to the first unanswered question.
            const firstUnanswered = data.questions.findIndex(
              (q) => !restored[q.question_id]
            );
            setCurrentIndex(firstUnanswered === -1 ? data.questions.length - 1 : firstUnanswered);
            setStarted(true);
          }
        } catch (progressErr) {
          // No saved progress yet - that's fine, just start fresh.
          console.log("No prior progress found", progressErr);
        }
      } catch (error) {
        console.error(error);
        setMessage("Could not load assessment questions.");
      } finally {
        setLoadingQuestions(false);
      }
    }

    if (candidateId) {
      loadQuestionsAndProgress();
    }
  }, [candidateId, jobId, role]);

  useEffect(() => {
    return () => {
      stopMediaStream();
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) return;

      tabSwitchCountRef.current += 1;
      setTabSwitchCount(tabSwitchCountRef.current);

      if (isRecordingRef.current) {
        // Mark for discard before stopping, so onstop() knows not to
        // save this take - the candidate must re-record from scratch.
        discardRecordingRef.current = true;
        mediaRecorderRef.current?.stop();
        if (timerRef.current) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setRecordingMode(null);
        setRecordingError(
          "Your recording was stopped because you left this tab. Please stay on this tab and record your answer again."
        );
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      // We deliberately exited fullscreen ourselves (candidate clicked
      // "Stop Recording") - not a violation, just reset and move on.
      if (intentionalFullscreenExitRef.current) {
        intentionalFullscreenExitRef.current = false;
        fullscreenActiveRef.current = false;
        return;
      }

      // Still in fullscreen - nothing happened.
      if (document.fullscreenElement) return;

      // Fullscreen was never actually active for this take (browser
      // doesn't support it, or entering it silently failed) - nothing
      // to enforce, don't penalize the candidate for their browser.
      if (!fullscreenActiveRef.current) return;

      // Not currently recording - fullscreen exit outside of a take
      // doesn't matter.
      if (!isRecordingRef.current) return;

      fullscreenActiveRef.current = false;
      fullscreenExitCountRef.current += 1;
      setFullscreenExitCount(fullscreenExitCountRef.current);

      // Same discard-and-retry treatment as a tab-switch violation.
      discardRecordingRef.current = true;
      mediaRecorderRef.current?.stop();
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRecordingMode(null);
      setRecordingError(
        "Your recording was stopped because you exited fullscreen mode. Please stay in fullscreen and record your answer again."
      );
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    const handleWindowBlur = () => {
      if (!isRecordingRef.current) return;

      focusLossCountRef.current += 1;
      setFocusLossCount(focusLossCountRef.current);

      // Same discard-and-retry treatment as the other two proctoring
      // signals. No "intentional" guard is needed here (unlike
      // fullscreen-exit) - nothing this component does programmatically
      // (clicking Stop Recording, requesting fullscreen) causes the
      // window itself to lose OS focus, so every blur while recording
      // is a genuine candidate action.
      discardRecordingRef.current = true;
      mediaRecorderRef.current?.stop();
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRecordingMode(null);
      setRecordingError(
        "Your recording was stopped because this window lost focus. Please stay on this window and record your answer again."
      );
    };

    window.addEventListener("blur", handleWindowBlur);
    return () => window.removeEventListener("blur", handleWindowBlur);
  }, []);

  const stopMediaStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const currentQuestion = questions[currentIndex];
  const isLastQuestion = currentIndex === questions.length - 1;
  const currentRecording = currentQuestion ? recordings[currentQuestion.question_id] : undefined;
  const isRecordingNow = recordingMode !== null;

  const startRecording = async (mode: ResponseMode) => {
    if (!currentQuestion) return;
    setRecordingError("");

    // Enter fullscreen first, before requesting media - this needs to
    // happen as close to the click as possible since browsers require
    // a user gesture to grant fullscreen. If the browser doesn't
    // support it (e.g. iPhone Safari has no Fullscreen API for
    // anything but a <video> element) or the request is denied, we
    // don't block recording - we just don't enforce fullscreen for
    // this take, so tab-switch protection still applies but this
    // extra layer silently doesn't for that candidate's browser.
    fullscreenActiveRef.current = false;
    if (fullscreenSupported) {
      try {
        await document.documentElement.requestFullscreen();
        fullscreenActiveRef.current = true;
      } catch {
        fullscreenActiveRef.current = false;
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: mode === "video",
      });

      streamRef.current = stream;
      chunksRef.current = [];

      if (mode === "video" && videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
        videoPreviewRef.current.muted = true;
        videoPreviewRef.current.play().catch(() => {});
      }

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        // If a tab-switch interrupted this recording, discard it
        // entirely rather than saving a partial/compromised take -
        // the candidate needs to re-record from scratch.
        if (discardRecordingRef.current) {
          discardRecordingRef.current = false;
          stopMediaStream();
          isRecordingRef.current = false;
          return;
        }

        const mimeType = mode === "video" ? "video/webm" : "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const blobUrl = URL.createObjectURL(blob);

        setRecordings((prev) => ({
          ...prev,
          [currentQuestion.question_id]: {
            mode,
            blobUrl,
            blob,
            durationSeconds: elapsedSecondsRef.current,
            savedRemotely: false,
          },
        }));

        stopMediaStream();
        isRecordingRef.current = false;
      };

      recorder.start();
      setRecordingMode(mode);
      isRecordingRef.current = true;
      setElapsedSeconds(0);
      elapsedSecondsRef.current = 0;

      timerRef.current = window.setInterval(() => {
        elapsedSecondsRef.current += 1;
        setElapsedSeconds(elapsedSecondsRef.current);
      }, 1000);
    } catch (err) {
      console.error(err);
      setRecordingError(
        "Could not access your microphone/camera. Please check browser permissions and try again."
      );
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecordingMode(null);

    // Exiting fullscreen here is a deliberate, candidate-initiated
    // stop, not a violation - mark it so the fullscreenchange listener
    // doesn't mistake this for exiting fullscreen mid-recording.
    if (document.fullscreenElement) {
      intentionalFullscreenExitRef.current = true;
      document.exitFullscreen().catch(() => {});
    }
  };

  const reRecord = () => {
    if (!currentQuestion) return;
    setRecordings((prev) => {
      const next = { ...prev };
      const existing = next[currentQuestion.question_id];
      if (existing?.blobUrl) URL.revokeObjectURL(existing.blobUrl);
      delete next[currentQuestion.question_id];
      return next;
    });
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const handleSaveAndContinue = async () => {
    if (!currentQuestion || !currentRecording) {
      setMessage("Please record an audio or video response before continuing.");
      return;
    }

    setSavingProgress(true);
    setMessage("");

    try {
      if (!currentRecording.savedRemotely) {
        await saveAssessmentProgress(candidateId, {
          question_id: currentQuestion.question_id,
          competency_key: currentQuestion.competency_key,
          mode: currentRecording.mode,
          duration_seconds: currentRecording.durationSeconds,
          tab_switch_count: tabSwitchCountRef.current,
          fullscreen_exit_count: fullscreenExitCountRef.current,
          focus_loss_count: focusLossCountRef.current,
        });

        if (currentRecording.blob) {
          try {
            await uploadRecording(
              candidateId,
              currentQuestion.question_id,
              currentRecording.mode,
              currentRecording.blob
            );
          } catch (uploadErr) {
            // Don't block the candidate's flow if the recording upload
            // fails - the score/progress is already saved either way.
            console.error("Recording upload failed:", uploadErr);
          }
        }

        setRecordings((prev) => ({
          ...prev,
          [currentQuestion.question_id]: { ...prev[currentQuestion.question_id], savedRemotely: true },
        }));
      }

      if (isLastQuestion) {
        await handleFinalSubmit();
      } else {
        setCurrentIndex((i) => i + 1);
      }
    } catch (err) {
      console.error(err);
      setMessage("Could not save your progress. Please try again.");
    } finally {
      setSavingProgress(false);
    }
  };

  const handleFinalSubmit = async () => {
    setLoadingAnalysis(true);
    setMessage("");
    setResult(null);

    try {
      const mappedAnswers: Record<string, string> = {};

      questions.forEach((question) => {
        const recording = recordings[question.question_id];
        mappedAnswers[question.competency_key] = recording
          ? `Candidate provided a ${recording.mode} response (duration ${formatDuration(recording.durationSeconds)}) to: "${question.question}"`
          : "";
      });

      const payload = {
        candidate_id: candidateId,
        job_id: jobId,
        role,
        stage: "pre_screen",
        answers: mappedAnswers,
      };

      const response = await analyzeAssessment(payload);
      setResult(response);
    } catch (error) {
      console.error(error);
      setMessage("Assessment submission failed.");
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const goToPrevious = () => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  };

  if (!candidateId) {
    return (
      <div className="ee-page">
        <div className="ee-empty">
          Apply first to start an assessment - your Candidate ID will carry over automatically.
        </div>
      </div>
    );
  }

  if (loadingQuestions) {
    return (
      <div className="ee-page">
        <div className="ee-page-header">
          <span className="ee-eyebrow">Pre-screening assessment</span>
          <h1>Loading your assessment</h1>
          <p>This should only take a moment.</p>
        </div>
      </div>
    );
  }

  if (result) {
    return (
      <div className="ee-page">
        <div className="ee-card ee-card--success" style={{ textAlign: "center", padding: "48px 32px" }}>
          <h1 style={{ marginBottom: 12 }}>Thank you</h1>
          <p style={{ fontSize: 16, lineHeight: 1.6 }}>
            Your responses have been submitted successfully. Our recruitment
            team will review your application and reach out if there's a
            good fit for the role.
          </p>
        </div>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="ee-page">
        <div className="ee-page-header">
          <span className="ee-eyebrow">Pre-screening assessment</span>
          <h1>Before you begin</h1>
        </div>

        <div className="ee-card">
          <p style={{ fontSize: 15, lineHeight: 1.6 }}>
            This screening includes <strong>{questions.length} questions</strong>. For each
            question, respond using either <strong>Audio</strong> or <strong>Video</strong> -
            aim for around 1-2 minutes per answer. You can choose audio or video separately
            for each question.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.6, marginTop: 12 }}>
            Your progress is saved after every question, so if you close this tab or lose
            connection, you can come back and pick up right where you left off.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.6, marginTop: 12 }}>
            <strong>This assessment is proctored.</strong> Recording will run in fullscreen
            mode. If you switch tabs, leave this window, exit fullscreen, or switch to a
            different application while recording, that recording will stop immediately and
            you'll need to record your answer again. These events are logged and visible to
            the recruiter reviewing your application.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.6, marginTop: 12 }}>
            <strong>Data Privacy:</strong> Your recorded answers are used only for the Equal
            Experts interview process and are never shared outside the company.
          </p>
          <button
            type="button"
            className="ee-btn ee-btn--primary"
            style={{ marginTop: 16 }}
            onClick={() => setStarted(true)}
          >
            Start assessment
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="ee-page">
      <div className="ee-page-header">
        <span className="ee-eyebrow">Pre-screening assessment</span>
        <h1>Answer with audio or video</h1>
      </div>

      <div className="ee-row" style={{ marginBottom: 20 }}>
        <span className="ee-badge ee-badge--brand">Candidate {candidateId.slice(0, 8)}</span>
        <span className="ee-badge ee-badge--neutral">{role}</span>
        {tabSwitchCount > 0 && (
          <span className="ee-badge ee-badge--danger">
            Tab switches: {tabSwitchCount}
          </span>
        )}
        {fullscreenExitCount > 0 && (
          <span className="ee-badge ee-badge--danger">
            Fullscreen exits: {fullscreenExitCount}
          </span>
        )}
        {focusLossCount > 0 && (
          <span className="ee-badge ee-badge--danger">
            Window focus lost: {focusLossCount}
          </span>
        )}
      </div>

      {recordingError && (
        <p className="ee-muted" style={{ color: "var(--danger)", marginBottom: 16 }}>{recordingError}</p>
      )}

      {currentQuestion && (
        <div className="ee-card">
          <div className="ee-progress">Question {currentIndex + 1} of {questions.length}</div>
          <h3 style={{ fontWeight: 500, lineHeight: 1.5, marginBottom: 16 }}>{currentQuestion.question}</h3>

          {!currentRecording && !isRecordingNow && (
            <div className="ee-row">
              <button type="button" className="ee-btn ee-btn--outline" onClick={() => startRecording("audio")}>
                &#127908; Record audio
              </button>
              <button type="button" className="ee-btn ee-btn--outline" onClick={() => startRecording("video")}>
                &#127909; Record video
              </button>
            </div>
          )}

          {isRecordingNow && (
            <div className="ee-card ee-card--highlight">
              <div className="ee-row--between">
                <span className="ee-badge ee-badge--danger">
                  &#9679; Recording {recordingMode} - {formatDuration(elapsedSeconds)}
                </span>
                <button type="button" className="ee-btn ee-btn--danger-outline" onClick={stopRecording}>
                  Stop recording
                </button>
              </div>

              {recordingMode === "video" && (
                <video
                  ref={videoPreviewRef}
                  style={{ width: "100%", maxWidth: 360, marginTop: 14, borderRadius: 8, background: "#000" }}
                />
              )}
            </div>
          )}

          {currentRecording && (
            <div>
              <div className="ee-row--between" style={{ marginBottom: 10 }}>
                <span className="ee-badge ee-badge--success">
                  {currentRecording.mode === "video" ? "\u{1F3A5}" : "\u{1F3A4}"} Recorded - {formatDuration(currentRecording.durationSeconds)}
                  {currentRecording.savedRemotely ? " (saved)" : ""}
                </span>
                <button type="button" className="ee-btn ee-btn--ghost" onClick={reRecord}>
                  Re-record
                </button>
              </div>

              {currentRecording.blobUrl ? (
                currentRecording.mode === "video" ? (
                  <video src={currentRecording.blobUrl} controls style={{ width: "100%", maxWidth: 360, borderRadius: 8 }} />
                ) : (
                  <audio src={currentRecording.blobUrl} controls style={{ width: "100%" }} />
                )
              ) : (
                <p className="ee-muted">This answer was saved in a previous session.</p>
              )}
            </div>
          )}

          <div className="ee-row" style={{ marginTop: 20 }}>
            {currentIndex > 0 && (
              <button type="button" className="ee-btn ee-btn--ghost" onClick={goToPrevious} disabled={savingProgress || loadingAnalysis}>
                Back
              </button>
            )}
            <button
              type="button"
              className="ee-btn ee-btn--primary"
              disabled={!currentRecording || savingProgress || loadingAnalysis}
              onClick={handleSaveAndContinue}
            >
              {loadingAnalysis
                ? "Submitting..."
                : savingProgress
                ? "Saving..."
                : isLastQuestion
                ? "Submit assessment"
                : "Save & Continue"}
            </button>
          </div>
        </div>
      )}

      {message && <p className="ee-muted" style={{ marginTop: 16 }}>{message}</p>}
    </div>
  );
}
