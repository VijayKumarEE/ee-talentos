import { useState, useRef, useEffect } from "react";
import { askCompanyChat, getFunFact, type CompanyChatDisplay } from "../api/client";

type ChatMessage = {
  sender: "bot" | "candidate";
  text: string;
  link?: string | null;
  // Present only on "surprise me" responses - renders as a brand-blue
  // fact card instead of the regular grey text bubble.
  fact?: { icon: string; stat: string | null; caption: string } | null;
  // Present on regular answers that have a richer visual treatment
  // (values, interview process, Glassdoor, company overview). Absent
  // means "render as the plain grey bubble," unchanged from before.
  display?: CompanyChatDisplay | null;
};

const GREETING: ChatMessage = {
  sender: "bot",
  text:
    "Hi! I can share information about Equal Experts - our LinkedIn page, " +
    "Glassdoor reviews, our values, the interview process, or a link to a " +
    "specific role's job description. What would you like to know?",
  link: null,
};

// Quick-reply chips shown above the input at all times. These exist so
// a candidate never has to guess what a chatbot can even answer -
// clicking one sends that exact text through the same path as typing
// it. "See open roles" deliberately doesn't try to guess a specific
// role - it routes to the general careers page, since this widget
// doesn't currently know which role the candidate selected above it.
//
// Each entry carries the `topic` the backend is expected to resolve
// it to. Once a topic has actually been answered (whether the
// candidate clicked its chip or just typed a question that resolved
// to the same topic), that chip disappears from the row - a
// candidate shouldn't be able to tap "Glassdoor reviews" repeatedly
// and see the same thing pop up again. This tracking is topic-based,
// not chip-based, so typing a question manually correctly removes
// the matching chip too.
const SUGGESTED_PROMPTS: { label: string; topic: string }[] = [
  { label: "Tell me about Equal Experts", topic: "company_overview" },
  { label: "What's the interview process?", topic: "interview_process" },
  { label: "What are your values?", topic: "values" },
  { label: "LinkedIn page", topic: "linkedin" },
  { label: "Glassdoor reviews", topic: "glassdoor" },
  { label: "See open roles", topic: "jd" },
  { label: "Life at Equal Experts", topic: "life_at_ee" },
  { label: "Meet the team", topic: "team" },
  { label: "Case studies", topic: "case_studies" },
];

// Only this many chips show at once, not all remaining unused ones -
// otherwise the suggestion row can grow to dominate the whole widget
// when few topics have been used yet. As a chip gets used and drops
// out of the filtered list, the next one already in SUGGESTED_PROMPTS
// automatically slides into view to keep this count topped up.
const MAX_VISIBLE_CHIPS = 4;

// Extracted as a standalone function (not inline JSX) specifically so
// `display` can be captured in a local `const` - TypeScript's
// discriminated-union narrowing on msg.display.type doesn't reliably
// persist into a nested .map() closure when accessed as a property
// each time, but it does persist correctly through a captured const.
function renderMessage(msg: ChatMessage, key: number) {
  if (msg.fact) {
    const fact = msg.fact;
    return (
      <div
        key={key}
        style={{
          alignSelf: "flex-start",
          maxWidth: "85%",
          background: "var(--brand-blue)",
          borderRadius: "var(--radius-md)",
          padding: "12px 14px",
          display: "flex",
          alignItems: fact.stat ? "center" : "flex-start",
          gap: 10,
        }}
      >
        <span style={{ fontSize: 22, lineHeight: 1 }}>{fact.icon}</span>
        <div>
          {fact.stat && (
            <div style={{ fontSize: 20, fontWeight: 700, color: "white", lineHeight: 1.2 }}>
              {fact.stat}
            </div>
          )}
          <div
            style={{
              fontSize: fact.stat ? 12 : 13,
              color: fact.stat ? "var(--brand-blue-tint-2)" : "white",
              marginTop: fact.stat ? 2 : 0,
              lineHeight: 1.5,
            }}
          >
            {fact.caption}
          </div>
        </div>
      </div>
    );
  }

  const display = msg.display;
  if (display) {
    return (
      <div
        key={key}
        style={{
          alignSelf: "flex-start",
          maxWidth: "88%",
          borderRadius: "var(--radius-md)",
          padding: "12px 14px",
          background: display.type === "stat_card" ? "var(--brand-blue)" : "var(--neutral-bg)",
        }}
      >
        {display.type === "stat_card" && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 22, lineHeight: 1 }}>{display.icon}</span>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "white", lineHeight: 1.2 }}>
                  {display.stat}
                </div>
                <div style={{ fontSize: 12, color: "var(--brand-blue-tint-2)", marginTop: 2, lineHeight: 1.5 }}>
                  {display.caption}
                </div>
              </div>
            </div>
            {msg.link && (
              <a
                href={msg.link}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-block",
                  marginTop: 10,
                  fontSize: 12,
                  fontWeight: 600,
                  color: "white",
                  textDecoration: "none",
                  border: "1px solid rgba(255,255,255,0.5)",
                  borderRadius: 6,
                  padding: "4px 10px",
                }}
              >
                Open link &rarr;
              </a>
            )}
          </>
        )}

        {display.type === "icon_list" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {display.items.map((item, idx) => (
              <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                <span style={{ fontSize: 14, lineHeight: 1.4, flexShrink: 0 }}>{display.icon}</span>
                <span style={{ fontSize: 13, lineHeight: 1.5, color: "var(--ink)" }}>{item}</span>
              </div>
            ))}
          </div>
        )}

        {display.type === "step_list" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {display.items.map((item, idx) => (
              <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    background: "var(--brand-blue)",
                    color: "white",
                    fontSize: 11,
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {idx + 1}
                </div>
                <span style={{ fontSize: 13, lineHeight: 1.5, color: "var(--ink)", paddingTop: 1 }}>{item}</span>
              </div>
            ))}
          </div>
        )}

        {display.type === "info_card" && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <span style={{ fontSize: 20, lineHeight: 1.4, flexShrink: 0 }}>{display.icon}</span>
            <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--ink)" }}>{display.caption}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      key={key}
      style={{
        alignSelf: msg.sender === "candidate" ? "flex-end" : "flex-start",
        maxWidth: "85%",
        background: msg.sender === "candidate" ? "var(--brand-blue-tint)" : "var(--neutral-bg)",
        color: "var(--ink)",
        borderRadius: "var(--radius-md)",
        padding: "8px 12px",
        fontSize: 14,
        lineHeight: 1.5,
        whiteSpace: "pre-wrap",
      }}
    >
      {msg.text}
      {msg.link && (
        <div style={{ marginTop: 8 }}>
          <a
            href={msg.link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-block",
              fontSize: 13,
              fontWeight: 600,
              color: "var(--brand-blue)",
              textDecoration: "none",
              border: "1px solid var(--brand-blue)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 10px",
            }}
          >
            Open link &rarr;
          </a>
        </div>
      )}
    </div>
  );
}

/**
 * Floating bottom-right widget, shown only on the candidate application
 * form (not during the assessment or on recruiter pages). Deliberately
 * scoped to company information only - it cannot discuss the
 * assessment questions, scoring, or anything else, since the backend
 * only ever returns one of a small set of pre-approved answers.
 */
export default function CompanyChatWidget() {
  const [open, setOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [usedTopics, setUsedTopics] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { sender: "candidate", text: trimmed }]);
    setInput("");
    setSending(true);

    try {
      const result = await askCompanyChat(trimmed);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: result.reply, link: result.link, display: result.display },
      ]);
      if (result.topic && result.topic !== "fallback") {
        setUsedTopics((prev) => new Set(prev).add(result.topic!));
      }
    } catch {
      // A genuine network failure (server unreachable, etc.) - a chat
      // bubble explaining that is much better UX here than a thrown
      // error, since this is a conversational widget, not a form.
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "Sorry, I couldn't process that right now. Please try again in a moment.",
          link: null,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleSurpriseMe = async () => {
    if (sending) return;

    setMessages((prev) => [...prev, { sender: "candidate", text: "\uD83C\uDFB2 Surprise me!" }]);
    setSending(true);

    try {
      const fact = await getFunFact();
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "", fact },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "Sorry, I couldn't fetch a fact right now. Please try again in a moment.",
          link: null,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 1000 }}>
      {open && (
        <div
          style={{
            width: 340,
            height: 440,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-md)",
            display: "flex",
            flexDirection: "column",
            marginBottom: 12,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 16px",
              background: "var(--brand-blue)",
              color: "white",
              fontFamily: "var(--font-display)",
              fontWeight: 600,
              fontSize: 15,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            Ask about Equal Experts
            <button
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              style={{
                background: "none",
                border: "none",
                color: "white",
                fontSize: 18,
                cursor: "pointer",
                lineHeight: 1,
                padding: 0,
              }}
            >
              &times;
            </button>
          </div>

          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: 14,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {messages.map((msg, i) => renderMessage(msg, i))}
            {sending && (
              <div
                style={{
                  alignSelf: "flex-start",
                  color: "var(--ink-muted)",
                  fontSize: 13,
                  fontStyle: "italic",
                }}
              >
                Typing...
              </div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              padding: "10px 10px 0 10px",
              borderTop: "1px solid var(--border)",
            }}
          >
            {SUGGESTED_PROMPTS.filter((prompt) => !usedTopics.has(prompt.topic)).slice(0, MAX_VISIBLE_CHIPS).map((prompt) => (
              <button
                key={prompt.topic}
                onClick={() => sendMessage(prompt.label)}
                disabled={sending}
                style={{
                  background: "var(--brand-blue-tint)",
                  color: "var(--brand-blue-deep)",
                  border: "1px solid var(--brand-blue-tint-2)",
                  borderRadius: 999,
                  padding: "5px 10px",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: sending ? "not-allowed" : "pointer",
                  opacity: sending ? 0.6 : 1,
                }}
              >
                {prompt.label}
              </button>
            ))}
            <button
              onClick={handleSurpriseMe}
              disabled={sending}
              style={{
                background: "var(--brand-blue)",
                color: "white",
                border: "1px solid var(--brand-blue)",
                borderRadius: 999,
                padding: "5px 10px",
                fontSize: 12,
                fontWeight: 600,
                cursor: sending ? "not-allowed" : "pointer",
                opacity: sending ? 0.6 : 1,
              }}
            >
              {"\uD83C\uDFB2 Surprise me!"}
            </button>
          </div>

          <div
            style={{
              display: "flex",
              padding: 10,
              gap: 8,
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the company or a role..."
              disabled={sending}
              style={{
                flex: 1,
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 10px",
                fontSize: 14,
                fontFamily: "var(--font-body)",
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={sending || !input.trim()}
              style={{
                background: "var(--brand-blue)",
                color: "white",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "0 14px",
                fontSize: 14,
                fontWeight: 600,
                cursor: sending || !input.trim() ? "not-allowed" : "pointer",
                opacity: sending || !input.trim() ? 0.6 : 1,
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((prev) => !prev)}
        aria-label={open ? "Close company chat" : "Open company chat"}
        style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: "var(--brand-blue)",
          color: "white",
          border: "none",
          boxShadow: "var(--shadow-md)",
          fontSize: 24,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginLeft: "auto",
        }}
      >
        {open ? "\u00d7" : "\uD83D\uDCAC"}
      </button>
    </div>
  );
}
