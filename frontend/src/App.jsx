import { useState, useEffect, useRef } from 'react';
import { useGameSocket } from './useGameSocket';
import ActionBar from './ActionBar';
import RosterScreen from './RosterScreen';
import './App.css';

const API = import.meta.env.VITE_API_URL || '';

export default function App() {
  const {
    messages,
    status,
    sessionData,
    setupProgress,
    shiftEndedData,
    sendCommand,
    startSession,
    pendingDecisions,
    dismissDecision,
  } = useGameSocket();
  const bottomRef = useRef(null);
  const [rosterDismissed, setRosterDismissed] = useState(false);
  const isReady = sessionData?.status === 'ready';
  const canInteract = status === 'connected' && rosterDismissed && isReady;

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Poll REST status every 8s to keep sidebar live without polluting message stream
  const [liveStatus, setLiveStatus] = useState(null);
  useEffect(() => {
    if (status !== 'connected' || !sessionData) return;
    const poll = async () => {
      try {
        const res = await fetch(`/session/${sessionData.session_id}/status`);
        if (res.ok) setLiveStatus(await res.json());
      } catch {}
    };
    poll();
    const id = setInterval(poll, 8000);
    return () => clearInterval(id);
  }, [status, sessionData]);

  useEffect(() => {
    if (status === 'idle' || status === 'disconnected') {
      setLiveStatus(null);
    }
  }, [status]);

  // Used by sidebar bay clicks
  const submit = (text) => {
    if (!text.trim()) return;
    sendCommand(text.trim());
  };

  // Prefer live REST status for sidebar; fall back to message-stream parsing
  const bays = liveStatus ? parseLiveBays(liveStatus) : parseBays(messages);
  const clock = liveStatus
    ? `${liveStatus.clock} — ${Math.max(0, Math.floor((96 - liveStatus.global_turn) * 5 / 60))}h${String(Math.max(0, (96 - liveStatus.global_turn) * 5 % 60)).padStart(2,'0')}m remaining`
    : parseClock(messages);
  const recentAlerts = messages.filter(m => ['result', 'warning', 'resident', 'error'].includes(m.source)).slice(-4).reverse();
  const activeBay = bays.find(bay => bay.active) || null;

  return (
    <div className="layout">

      {/* LEFT PANEL — shift status */}
      <aside className="panel-left">
        <div className="panel-header">
          SHIFT STATUS
          {clock && <span className="clock">{clock}</span>}
        </div>

        {bays.length > 0 ? (
          <div className="bay-list">
            {bays.map(bay => (
              <div
                key={bay.id}
                className={`bay-card bay-clickable ${bay.active ? 'bay-active' : ''} ${bay.urgent ? 'bay-urgent' : ''}`}
                onClick={() => submit(`go ${bay.id.replace('Bay ', '')}`)}
                title={`Go to ${bay.id}`}
              >
                <div className="bay-top">
                  <span className="bay-id">{bay.id}</span>
                  <span className={`bay-acuity acuity-${bay.acuity}`}>[{bay.acuity}]</span>
                </div>
                <div className="bay-name">{bay.name}</div>
                <div className="bay-meta">
                  <span className={`bay-status status-${bay.status}`}>{bay.status}</span>
                  {bay.timer && <span className="bay-timer">{bay.timer}</span>}
                  {bay.pending && <span className="bay-pending">{bay.pending}</span>}
                </div>
                {bay.resident && <div className="bay-resident">{bay.resident}</div>}
                {bay.demoTitle && <div className="bay-demo-title">{bay.demoTitle}</div>}
              </div>
            ))}
          </div>
        ) : sessionData ? (
          <div className="bay-list">
            {sessionData.bays.map(b => (
              <div
                key={b.bay_id}
                className="bay-card bay-clickable"
                onClick={() => submit(`go ${b.bay_id}`)}
                title={`Go to Bay ${b.bay_id}`}
              >
                <div className="bay-top">
                  <span className="bay-id">{b.bay_id}</span>
                  <span className={`bay-acuity acuity-${b.acuity}`}>[{b.acuity}]</span>
                </div>
                <div className="bay-name">{b.patient_name}</div>
                <div className="bay-resident">{b.resident}</div>
                {b.demo_title && <div className="bay-demo-title">{b.demo_title}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-empty">No shift active</div>
        )}

        {status === 'connected' && (
          <div className="connection-dot connected">● connected</div>
        )}
        {status === 'connecting' && (
          <div className="connection-dot connecting">● connecting…</div>
        )}
        {status === 'disconnected' && (
          <div className="connection-dot disconnected">● disconnected</div>
        )}
      </aside>

      {/* MAIN PANEL — message stream + input */}
      <main className="panel-main">
        {canInteract && (
          <div className="mission-bar">
            <div className="mission-card">
              <div className="mission-label">Shift Goal</div>
              <div className="mission-text">Resolve cases, catch the trap case, and avoid unattended fires.</div>
            </div>
            <div className="mission-card mission-card-focus">
              <div className="mission-label">{activeBay ? `Current Focus — ${activeBay.id}` : 'Next Move'}</div>
              <div className="mission-text">
                {activeBay
                  ? `${activeBay.name}${activeBay.resident ? ` with ${activeBay.resident}` : ''}. ${activeBay.pending ? `${activeBay.pending}. ` : ''}${activeBay.timer ? `${activeBay.timer}. ` : ''}${activeBay.guidance || 'Talk, exam, order, or chart before dispo.'}`
                  : 'Pick a bay from the left. If you are unsure, start with the most urgent card or type status.'}
              </div>
            </div>
            <div className="mission-card">
              <div className="mission-label">If Stuck</div>
              <div className="mission-text">Ask the resident for their read, talk to the patient, then use chart once results return.</div>
            </div>
          </div>
        )}

        {canInteract && recentAlerts.length > 0 && (
          <div className="alert-rail">
            {recentAlerts.map(alert => (
              <div key={alert.id} className={`alert-chip alert-chip-${alert.source}`}>
                <div className="alert-chip-label">{alert.source.toUpperCase()}</div>
                <div className="alert-chip-text">{summarizeAlert(alert.text)}</div>
              </div>
            ))}
          </div>
        )}

        <div className="message-stream">

          {status === 'idle' && (
            <div className="splash">
              <div className="splash-kicker">Flagship Alpha Demo</div>
              <div className="splash-title">ERSim</div>
              <div className="splash-sub">Emergency department supervision under pressure.</div>
              <div className="splash-premise">
                Supervise 3 residents, catch the wrong frame, and keep the department stable.
              </div>
              <div className="splash-meta">
                <span>Flagship shift</span>
                <span>8-10 minutes</span>
                <span>Built for feedback</span>
              </div>
              <button className="start-btn" onClick={() => { setRosterDismissed(false); startSession(); }}>
                START FLAGSHIP SHIFT
              </button>
            </div>
          )}

          {/* Roster screen — show while assessments generate in background */}
          {sessionData?.roster && !rosterDismissed && (
            <RosterScreen
              roster={sessionData.roster}
              onBegin={() => setRosterDismissed(true)}
            />
          )}

          {/* Only show message stream after roster is dismissed */}
          {rosterDismissed && !isReady && sessionData && (
            <div className="setup-panel">
              <div className="setup-panel-header">
              <span className="spinner-dots">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </span>
                <div>
                  <div className="setup-title">Building resident reads</div>
                  <div className="setup-subtitle">
                    {setupProgress?.currentBay
                      ? `Latest complete: ${setupProgress.currentBay}`
                      : 'Generating first-pass assessments for each bay.'}
                  </div>
                </div>
              </div>

              <div className="setup-progress-row">
                <div className="setup-progress-label">
                  {setupProgress?.total
                    ? `${setupProgress.completed}/${setupProgress.total} bays ready`
                    : 'Preparing shift…'}
                </div>
                <div className="setup-progress-bar">
                  <div
                    className="setup-progress-fill"
                    style={{
                      width: setupProgress?.total
                        ? `${(setupProgress.completed / setupProgress.total) * 100}%`
                        : '10%',
                    }}
                  />
                </div>
              </div>

              <div className="setup-checklist">
                {sessionData.bays.map((bay, idx) => {
                  const completed = setupProgress?.doneBays?.includes(bay.bay_id) || false;
                  const active = !completed && setupProgress?.currentBay === bay.bay_id;
                  return (
                    <div key={bay.bay_id} className={`setup-check ${completed ? 'done' : ''} ${active ? 'active' : ''}`}>
                      <div className="setup-check-top">
                        <span>{bay.bay_id}</span>
                        <span className={`bay-acuity acuity-${bay.acuity}`}>[{bay.acuity}]</span>
                      </div>
                      <div className="setup-check-name">{bay.patient_name}</div>
                      <div className="setup-check-meta">{bay.resident}</div>
                      <div className="setup-check-state">
                        {completed ? 'Resident ready' : active ? 'Generating read…' : 'Queued'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {rosterDismissed && messages.map(msg => (
            <MessageBlock key={msg.id} msg={msg} sendCommand={sendCommand} />
          ))}

          <div ref={bottomRef} />
        </div>

        {/* Cross-bay decision banners */}
        {canInteract && pendingDecisions.length > 0 && (
          <div className="decision-banners">
            {pendingDecisions.map(d => (
              <div key={d.id} className="decision-banner">
                <div className="decision-header">
                  ⚡ {d.bay_id.toUpperCase()} — {d.resident_name} needs a decision
                </div>
                <div className="decision-text">{d.text}</div>
                <div className="decision-actions">
                  {d.options.map(opt => (
                    <button
                      key={opt.value}
                      className="decision-btn"
                      onClick={() => {
                        sendCommand(`respond ${d.bay_id} ${opt.value}`);
                        dismissDecision(d.id);
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                  <button
                    className="decision-btn decision-btn-dismiss"
                    onClick={() => dismissDecision(d.id)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Action bar + text input */}
        {canInteract && (
          <ActionBar sendCommand={sendCommand} />
        )}

        {status === 'disconnected' && shiftEndedData && (
          <div className="post-run-panel">
            <FeedbackPanel
              apiBase={API}
              sessionId={sessionData?.session_id}
              buildVersion={sessionData?.build_version || 'alpha-local'}
              feedbackContext={shiftEndedData.feedbackContext}
            />
            <div className="input-bar">
              <button className="start-btn small" onClick={() => { setRosterDismissed(false); startSession(); }}>
                NEW SHIFT
              </button>
            </div>
          </div>
        )}
      </main>

    </div>
  );
}


// ---------------------------------------------------------------------------
// MessageBlock — renders one message with source-based styling
// ---------------------------------------------------------------------------

function MessageBlock({ msg, sendCommand }) {
  const cls = `msg msg-${msg.source}`;
  const lineCount = (msg.text?.match(/\n/g)?.length ?? 0) + 1;
  const isLong = msg.text?.length > 500 || lineCount > 9;
  const collapsedSummary = summarizeCollapsedMessage(msg);

  // Detect the approval menu pattern
  const approvalPattern = /^([\s\S]*?)(?:>\s*)?1\.\s*Go ahead\s*\n\s*2\.\s*Go ahead, but add something\s*\n\s*3\.\s*Change the direction\s*\n\s*4\.\s*Hold\s*[—\-–]\s*I want to talk to the patient first\s*$/;
  const approvalMatch = msg.text?.match(approvalPattern);

  const approvalOptions = [
    { key: '1', label: '1. Go ahead' },
    { key: '2', label: '2. Go ahead, but add something' },
    { key: '3', label: '3. Change the direction' },
    { key: '4', label: '4. Hold — talk to patient first' },
  ];

  return (
    <div className={cls}>
      {msg.source === 'command' && (
        <span className="msg-prefix">&gt; </span>
      )}
      {msg.source === 'result' && (
        <span className="msg-prefix">** </span>
      )}
      {msg.source === 'autonomous' && (
        <span className="msg-prefix">!! </span>
      )}
      {approvalMatch ? (
        <span className="msg-text">
          {approvalMatch[1] && <span>{approvalMatch[1]}</span>}
          <span className="approval-buttons">
            {approvalOptions.map(opt => (
              <button
                key={opt.key}
                className="approval-btn"
                onClick={() => sendCommand(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </span>
        </span>
      ) : msg.type === 'shift_ended' ? (
        <DebriefCard text={msg.text} />
      ) : isLong ? (
        <details className={`msg-details ${isChartMessage(msg.text) ? 'msg-details-chart' : ''}`}>
          <summary className={`msg-summary ${isChartMessage(msg.text) ? 'msg-summary-chart' : ''}`}>{collapsedSummary}</summary>
          <span className="msg-text">{renderStructuredText(msg.text)}</span>
        </details>
      ) : (
        <span className="msg-text">{renderStructuredText(msg.text)}</span>
      )}
      <span className="msg-ts">{msg.ts}</span>
    </div>
  );
}

function DebriefCard({ text }) {
  const parsed = parseDebrief(text);

  return (
    <div className="debrief-card">
      <div className="debrief-header">
        <div className="debrief-title">Shift Debrief</div>
        {parsed.grade && <div className="debrief-grade">{parsed.grade}</div>}
      </div>
      <div className="debrief-highlights">
        {parsed.headline && <div className="debrief-chip"><span>Headline</span>{parsed.headline}</div>}
        {parsed.highlight && <div className="debrief-chip"><span>Highlight</span>{parsed.highlight}</div>}
        {parsed.watchout && <div className="debrief-chip debrief-chip-watchout"><span>Watchout</span>{parsed.watchout}</div>}
        {parsed.nextRep && <div className="debrief-chip"><span>Next Rep</span>{parsed.nextRep}</div>}
      </div>
      <details className="msg-details debrief-details">
        <summary className="msg-summary">Open full debrief</summary>
        <span className="msg-text">{renderStructuredText(text)}</span>
      </details>
    </div>
  );
}

function parseDebrief(text) {
  const lines = (text || '').split('\n');
  const pick = (prefix) => lines.find(line => line.startsWith(prefix))?.slice(prefix.length).trim() || '';
  const gradeLine = lines.find(line => line.includes('SHIFT GRADE:')) || '';
  return {
    headline: pick('Headline:'),
    highlight: pick('Highlight:'),
    watchout: pick('Watchout:'),
    nextRep: pick('Next rep:'),
    grade: gradeLine.split('SHIFT GRADE:')[1]?.trim() || '',
  };
}

function FeedbackPanel({ apiBase, sessionId, buildVersion, feedbackContext }) {
  const [testerRole, setTesterRole] = useState('product/tech');
  const [overallRating, setOverallRating] = useState('4');
  const [bestMoment, setBestMoment] = useState('');
  const [mostConfusingPart, setMostConfusingPart] = useState('');
  const [wouldUseAgain, setWouldUseAgain] = useState('yes');
  const [optionalContact, setOptionalContact] = useState('');
  const [submitState, setSubmitState] = useState('idle');
  const [errorText, setErrorText] = useState('');

  const canSubmit = bestMoment.trim() && mostConfusingPart.trim() && submitState !== 'submitting' && submitState !== 'done';

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitState('submitting');
    setErrorText('');
    try {
      const res = await fetch(`${apiBase}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: feedbackContext?.session_id || sessionId || '',
          build_version: feedbackContext?.build_version || buildVersion || 'alpha-local',
          shift_mode: feedbackContext?.shift_mode || 'flagship',
          debrief_grade: feedbackContext?.grade || '',
          tester_role: testerRole,
          overall_rating: Number(overallRating),
          best_moment: bestMoment.trim(),
          most_confusing_part: mostConfusingPart.trim(),
          would_you_use_again: wouldUseAgain === 'yes',
          optional_contact: optionalContact.trim(),
          metrics: feedbackContext?.metrics || {},
        }),
      });
      if (!res.ok) {
        throw new Error(`Feedback save failed (${res.status})`);
      }
      setSubmitState('done');
    } catch (error) {
      setSubmitState('idle');
      setErrorText(error.message || 'Feedback save failed.');
    }
  };

  return (
    <form className="feedback-card" onSubmit={handleSubmit}>
      <div className="feedback-header">
        <div>
          <div className="feedback-title">Tell us how that run felt</div>
          <div className="feedback-subtitle">
            Short feedback helps sharpen the next alpha build.
          </div>
        </div>
        {feedbackContext?.grade && (
          <div className="feedback-grade">Grade {feedbackContext.grade}</div>
        )}
      </div>

      <div className="feedback-grid">
        <label className="feedback-field">
          <span>Your lens</span>
          <select value={testerRole} onChange={(e) => setTesterRole(e.target.value)}>
            <option value="clinician">Clinician</option>
            <option value="medical trainee">Medical trainee</option>
            <option value="product/tech">Product/tech</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label className="feedback-field">
          <span>Overall rating</span>
          <select value={overallRating} onChange={(e) => setOverallRating(e.target.value)}>
            <option value="5">5 - loved it</option>
            <option value="4">4 - strong</option>
            <option value="3">3 - mixed</option>
            <option value="2">2 - weak</option>
            <option value="1">1 - not working</option>
          </select>
        </label>

        <label className="feedback-field">
          <span>Would you use it again?</span>
          <select value={wouldUseAgain} onChange={(e) => setWouldUseAgain(e.target.value)}>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>

        <label className="feedback-field">
          <span>Optional contact</span>
          <input
            value={optionalContact}
            onChange={(e) => setOptionalContact(e.target.value)}
            placeholder="email or handle"
            autoComplete="off"
          />
        </label>
      </div>

      <label className="feedback-field feedback-field-textarea">
        <span>Best moment</span>
        <textarea
          value={bestMoment}
          onChange={(e) => setBestMoment(e.target.value)}
          placeholder="What landed best or felt most memorable?"
          rows={3}
        />
      </label>

      <label className="feedback-field feedback-field-textarea">
        <span>Most confusing part</span>
        <textarea
          value={mostConfusingPart}
          onChange={(e) => setMostConfusingPart(e.target.value)}
          placeholder="What felt unclear, clunky, or hard to read?"
          rows={3}
        />
      </label>

      <div className="feedback-actions">
        <button className="start-btn small" type="submit" disabled={!canSubmit}>
          {submitState === 'submitting' ? 'SAVING...' : submitState === 'done' ? 'FEEDBACK SAVED' : 'SEND FEEDBACK'}
        </button>
        {errorText && <div className="feedback-error">{errorText}</div>}
        {submitState === 'done' && <div className="feedback-thanks">Thanks. Your notes were saved with this run.</div>}
      </div>
    </form>
  );
}

function summarizeAlert(text) {
  if (!text) return '';
  const firstMeaningfulLine = text
    .split('\n')
    .map(line => line.trim())
    .find(line => line && !line.startsWith('---'));
  if (!firstMeaningfulLine) return text.slice(0, 140);
  return firstMeaningfulLine.length > 140
    ? `${firstMeaningfulLine.slice(0, 137)}...`
    : firstMeaningfulLine;
}

function isChartMessage(text) {
  return text?.includes('--- CHART:');
}

function summarizeCollapsedMessage(msg) {
  const text = msg?.text || '';
  const firstLine = text
    .split('\n')
    .map(line => line.trim())
    .find(Boolean) || '';
  if (msg?.type === 'shift_ended' || text.includes('SHIFT DEBRIEF')) {
    return 'Open shift debrief';
  }
  if (isChartMessage(text)) {
    const reveal = text.match(/--- (?:REVEALED|WHAT YOU LEARNED) \((\d+)\) ---/);
    const locked = text.match(/--- (?:STILL LOCKED|STILL HIDDEN) \((\d+)\) ---/);
    const pending = text.match(/Pending: ([^\n]+)/);
    const family = text.match(/Family present: ([^\n]+)/i);
    const bits = [];
    if (reveal) bits.push(`${reveal[1]} reveals open`);
    if (locked) bits.push(`${locked[1]} still locked`);
    if (pending) bits.push(`pending ${pending[1]}`);
    if (family) bits.push(`family ${family[1].trim().toLowerCase() === 'true' ? 'in room' : 'not in room'}`);
    return `Open chart - ${bits.join(' • ') || 'expand patient chart'}`;
  }
  if (firstLine.startsWith('Tests ordered:')) {
    return 'Open ordered tests';
  }
  if (firstLine.startsWith('[Bay ')) {
    return `Open result update - ${firstLine}`;
  }
  if (/^\[[A-Z0-9 .'\-]+\]:/.test(firstLine)) {
    return `Open bedside response - ${firstLine.slice(0, 90)}${firstLine.length > 90 ? '...' : ''}`;
  }
  if (firstLine.startsWith('[')) {
    return `Open update - ${firstLine.slice(0, 90)}${firstLine.length > 90 ? '...' : ''}`;
  }
  if (text.length > 180) {
    return `Open update - ${summarizeAlert(text)}`;
  }
  return summarizeAlert(text);
}

function renderStructuredText(text) {
  const sections = text.split(/\n{2,}/).filter(Boolean);
  return sections.map((section, idx) => (
    <span key={idx} className="msg-section">
      {section.split('\n').map((line, lineIdx) => (
        <span
          key={`${idx}-${lineIdx}`}
          className={lineClassName(line)}
        >
          {formatDisplayLine(line)}
        </span>
      ))}
    </span>
  ));
}

function formatDisplayLine(line) {
  if (/^Family present:\s*False$/i.test(line)) return 'Family: not in room';
  if (/^Family present:\s*True$/i.test(line)) return 'Family: in room';
  if (line.startsWith('Pending: ')) return `Pending results: ${line.slice('Pending: '.length)}`;
  if (line.startsWith('Tests ordered: ')) return `Orders in flight: ${line.slice('Tests ordered: '.length)}`;
  return line;
}

function lineClassName(line) {
  if (line.startsWith('---')) return 'msg-line msg-line-rule';
  if (line.startsWith('[')) return 'msg-line msg-line-callout';
  if (line.trim().startsWith('!')) return 'msg-line msg-line-flag';
  if (line.includes('Tests ordered:') || line.includes('Pending:')) return 'msg-line msg-line-meta';
  if (line.includes('Outcome:') || line.includes('Correct disposition.') || line.includes('Should have been:')) return 'msg-line msg-line-outcome';
  return 'msg-line';
}


// ---------------------------------------------------------------------------
// Helpers — parse bay status and clock from message stream
// ---------------------------------------------------------------------------

function parseBays(messages) {
  // Find the most recent status message and parse bay lines from it
  const statusMsgs = [...messages].reverse().filter(
    m => m.text?.includes('STATUS') && m.text?.includes('Bay')
  );
  if (!statusMsgs.length) return [];

  const text = statusMsgs[0].text;
  const lines = text.split('\n');
  const bays = [];

  for (const line of lines) {
    // Match lines like: ">> Bay 1  [2]  Jennifer Kowalski    ACTIVE       !! ACTING SOON  (3 pending)"
    const m = line.match(/^(>>|   )\s*(Bay \d+)\s+\[(\d)\]\s+(.+?)\s{2,}(\w+)\s*(.*?)$/);
    if (m) {
      const [, marker, id, acuity, name, statusRaw, rest] = m;
      const active = marker.trim() === '>>';
      const status = statusRaw.toLowerCase();
      const urgent = rest.includes('ACTING') || rest.includes('!!');
      const timerMatch = rest.match(/(\d+ actions?|!! ACTING SOON)/);
      const pendingMatch = rest.match(/\((\d+) pending\)/);
      // Extract resident from name if it's in there — it's not, resident is in bay card separately
      bays.push({
        id,
        acuity,
        name: name.trim(),
        status,
        active,
        urgent,
        timer: timerMatch ? timerMatch[1] : null,
        pending: pendingMatch ? `${pendingMatch[1]} pending` : null,
        resident: null,
      });
    }
  }
  return bays;
}

function parseLiveBays(liveStatus) {
  if (!liveStatus?.bays) return [];
  return liveStatus.bays.map(b => ({
    id: b.bay_id,
    acuity: b.acuity,
    name: b.patient_name,
    status: b.status,
    active: b.bay_id === liveStatus.active_bay,
    urgent: b.timer_pressure === 'critical' || b.timer_pressure === 'high',
    timer: b.timer_pressure && b.timer_pressure !== 'none'
      ? `${b.timer_pressure} pressure`
      : null,
    pending: b.pending_results > 0 ? `${b.pending_results} pending` : null,
    resident: b.resident || null,
    summary: b.triage_summary || null,
    guidance: b.guidance || null,
    demoTitle: b.demo_title || null,
  }));
}

function parseClock(messages) {
  const statusMsgs = [...messages].reverse().filter(
    m => m.text?.includes('STATUS') && m.text?.includes('remaining')
  );
  if (!statusMsgs.length) return null;
  const m = statusMsgs[0].text.match(/\[(\d{2}:\d{2}\s+—\s+\S+\s+remaining)\]/);
  return m ? m[1] : null;
}
