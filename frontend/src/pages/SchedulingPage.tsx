import { useState } from "react";
import { getCandidateSlots, bookSlot } from "../api/client";

type Slot = {
  slot_id: string;
  panel: string;
  start: string;
  end: string;
  label: string;
};

type Round = "recruiter" | "panel";

export default function SchedulingPage() {
  const [candidateIdInput, setCandidateIdInput] = useState("");
  const [round, setRound] = useState<Round>("recruiter");

  const [slots, setSlots] = useState<Slot[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [bookingSlotId, setBookingSlotId] = useState<string | null>(null);

  const [bookedSlot, setBookedSlot] = useState<Slot | null>(null);
  const [message, setMessage] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  const handleFindSlots = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!candidateIdInput.trim()) {
      setMessage("Enter your Candidate ID to continue.");
      return;
    }

    setLoadingSlots(true);
    setMessage("");
    setBookedSlot(null);
    setHasSearched(true);

    try {
      const data = await getCandidateSlots(candidateIdInput.trim(), round);
      setSlots(data.slots || []);

      if (!data.slots || data.slots.length === 0) {
        setMessage(
          "No times available yet for this round - check back after your recruiter shortlists you."
        );
      }
    } catch (err) {
      console.error(err);
      setMessage("Could not load times. Check your Candidate ID and try again.");
      setSlots([]);
    } finally {
      setLoadingSlots(false);
    }
  };

  const handleBook = async (slot: Slot) => {
    setBookingSlotId(slot.slot_id);
    setMessage("");

    try {
      const result = await bookSlot(candidateIdInput.trim(), slot.slot_id, round);
      setBookedSlot(result.booked_slot || slot);
    } catch (err) {
      console.error(err);
      setMessage("That time was just taken - please pick another.");
    } finally {
      setBookingSlotId(null);
    }
  };

  return (
    <div className="ee-page">
      <div className="ee-page-header">
        <span className="ee-eyebrow">Interview scheduling</span>
        <h1>Pick a time that works</h1>
        <p>Enter your Candidate ID from your invitation email, then choose a slot.</p>
      </div>

      <div className="ee-card">
        <form onSubmit={handleFindSlots}>
          <div className="ee-field">
            <label className="ee-label">Candidate ID</label>
            <input
              className="ee-input"
              placeholder="e.g. 9f9bf345-ab1f-4b0e-9336-7cf427545770"
              value={candidateIdInput}
              onChange={(e) => setCandidateIdInput(e.target.value)}
            />
          </div>

          <div className="ee-field">
            <label className="ee-label">Interview round</label>
            <select className="ee-select" value={round} onChange={(e) => setRound(e.target.value as Round)}>
              <option value="recruiter">Recruiter screen</option>
              <option value="panel">Panel interview</option>
            </select>
          </div>

          <button type="submit" className="ee-btn ee-btn--primary" disabled={loadingSlots}>
            {loadingSlots ? "Loading..." : "Find available times"}
          </button>
        </form>
      </div>

      {message && <p className="ee-muted" style={{ marginTop: 16 }}>{message}</p>}

      {bookedSlot && (
        <div className="ee-card ee-card--success" style={{ marginTop: 20 }}>
          <span className="ee-badge ee-badge--success">Confirmed</span>
          <h2 style={{ marginTop: 12 }}>{bookedSlot.label}</h2>
          <p style={{ marginTop: 8 }}>
            A confirmation has been sent - you're all set for your interview.
          </p>
        </div>
      )}

      {!bookedSlot && hasSearched && slots.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ marginBottom: 12 }}>Available times</h3>
          <div className="ee-stack">
            {slots.map((slot) => (
              <div key={slot.slot_id} className="ee-card ee-row--between" style={{ padding: "16px 20px" }}>
                <span style={{ fontWeight: 500 }}>{slot.label}</span>
                <button
                  type="button"
                  className="ee-btn ee-btn--outline"
                  disabled={bookingSlotId === slot.slot_id}
                  onClick={() => handleBook(slot)}
                >
                  {bookingSlotId === slot.slot_id ? "Booking..." : "Book this time"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
