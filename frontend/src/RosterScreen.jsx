/**
 * RosterScreen — pre-shift resident briefing.
 *
 * Shows who's on tonight, their style, strengths, and what to watch for.
 * Player reads this like a real attending checking the board, then clicks
 * BEGIN SHIFT to start generating assessments.
 */

export default function RosterScreen({ roster, onBegin }) {
  if (!roster || roster.length === 0) return null;

  return (
    <div className="roster-screen">
      <div className="roster-header">
        <div className="roster-title">FLAGSHIP SHIFT TEAM</div>
        <div className="roster-sub">Know who is on tonight, then start the strongest version of the alpha demo.</div>
      </div>

      <div className="roster-cards">
        {roster.map(r => (
          <div key={r.bay_id} className="roster-card">
            <div className="roster-card-top">
              <span className="roster-name">{r.name}</span>
              <span className="roster-year">{r.year}</span>
            </div>

            <div className="roster-style">{r.style}</div>

            <div className="roster-section">
              <span className="roster-label">Strengths:</span>
              <ul className="roster-list">
                {r.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>

            <div className="roster-section">
              <span className="roster-label">Watch for:</span>
              <ul className="roster-list watch">
                {r.watch_for.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>

            <div className="roster-backstory">{r.backstory}</div>

            <div className="roster-assignment">
              → {r.bay_id}: {r.patient_name}
              <span className={`roster-acuity acuity-${r.acuity}`}> [{r.acuity}]</span>
              <span className="roster-cc"> — {r.chief_complaint}</span>
            </div>
          </div>
        ))}
      </div>

      <button className="roster-begin-btn" onClick={onBegin}>
        START FLAGSHIP SHIFT →
      </button>
    </div>
  );
}
