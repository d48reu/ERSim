import { useState, useEffect, useRef } from 'react';
import { useGameSocket } from './useGameSocket';
import './App.css';

export default function App() {
  const { messages, status, sessionData, sendCommand, startSession } = useGameSocket();
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const [histIdx, setHistIdx] = useState(-1);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when connected
  useEffect(() => {
    if (status === 'connected') inputRef.current?.focus();
  }, [status]);

  const submit = (text) => {
    if (!text.trim()) return;
    sendCommand(text.trim());
    setHistory(h => [text.trim(), ...h.slice(0, 49)]);
    setHistIdx(-1);
    setInput('');
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') {
      submit(input);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = Math.min(histIdx + 1, history.length - 1);
      setHistIdx(idx);
      setInput(history[idx] || '');
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const idx = Math.max(histIdx - 1, -1);
      setHistIdx(idx);
      setInput(idx === -1 ? '' : history[idx] || '');
    }
  };

  // Parse bay status lines out of the latest status message
  const bays = parseBays(messages);
  const clock = parseClock(messages);

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
              <div key={bay.id} className={`bay-card ${bay.active ? 'bay-active' : ''} ${bay.urgent ? 'bay-urgent' : ''}`}>
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
              </div>
            ))}
          </div>
        ) : sessionData ? (
          <div className="bay-list">
            {sessionData.bays.map(b => (
              <div key={b.bay_id} className="bay-card">
                <div className="bay-top">
                  <span className="bay-id">{b.bay_id}</span>
                  <span className={`bay-acuity acuity-${b.acuity}`}>[{b.acuity}]</span>
                </div>
                <div className="bay-name">{b.patient_name}</div>
                <div className="bay-resident">{b.resident}</div>
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
        <div className="message-stream">

          {status === 'idle' && (
            <div className="splash">
              <div className="splash-title">ERSim</div>
              <div className="splash-sub">Emergency Department Management Simulation</div>
              <button className="start-btn" onClick={startSession}>
                START SHIFT
              </button>
            </div>
          )}

          {status === 'connecting' && messages.length === 0 && (
            <div className="connecting-msg">Generating shift…</div>
          )}

          {messages.map(msg => (
            <MessageBlock key={msg.id} msg={msg} />
          ))}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        {(status === 'connected') && (
          <div className="input-bar">
            <span className="input-prompt">
              {'>'}
            </span>
            <input
              ref={inputRef}
              className="input-field"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="go 1  /  exam abdomen  /  1  /  talk to patient…"
              autoComplete="off"
              spellCheck="false"
            />
          </div>
        )}

        {status === 'disconnected' && messages.length > 0 && (
          <div className="input-bar">
            <button className="start-btn small" onClick={startSession}>
              NEW SHIFT
            </button>
          </div>
        )}
      </main>

    </div>
  );
}


// ---------------------------------------------------------------------------
// MessageBlock — renders one message with source-based styling
// ---------------------------------------------------------------------------

function MessageBlock({ msg }) {
  const cls = `msg msg-${msg.source}`;
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
      <span className="msg-text">{msg.text}</span>
      <span className="msg-ts">{msg.ts}</span>
    </div>
  );
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

function parseClock(messages) {
  const statusMsgs = [...messages].reverse().filter(
    m => m.text?.includes('STATUS') && m.text?.includes('remaining')
  );
  if (!statusMsgs.length) return null;
  const m = statusMsgs[0].text.match(/\[(\d{2}:\d{2}\s+—\s+\S+\s+remaining)\]/);
  return m ? m[1] : null;
}
