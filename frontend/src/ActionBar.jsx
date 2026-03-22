/**
 * ActionBar — clickable command interface with drill-down submenus.
 *
 * State machine modes:
 *   top           → show action buttons + free-text input
 *   exam          → body part picker
 *   test          → common tests + custom input
 *   talk-patient  → free-text input (focused)
 *   talk-resident → preset questions + custom input
 *   disposition   → admit-floor / admit-icu / discharge / transfer
 */

import { useState, useRef, useEffect } from 'react';

const EXAM_PARTS = [
  'Head', 'Chest', 'Abdomen', 'Extremities', 'Neuro', 'Skin',
  'Lymph Node', 'Back/Spine', 'Cardiac', 'Pelvis',
];

const COMMON_TESTS = [
  'CBC', 'BMP', 'CMP', 'Troponin', 'Lactate', 'UA', 'EKG',
  'Chest X-Ray', 'CT Head', 'CT Abdomen', 'Blood Cultures',
  'Rapid Flu', 'D-Dimer', 'Lipase', 'VBG',
];

const RESIDENT_PRESETS = [
  { label: "What's your read?", cmd: 'ask What is your read on this patient?' },
  { label: "What changed?", cmd: 'ask What changed since we last talked?' },
  { label: "Run the plan", cmd: '1' },
  { label: "Hold the plan", cmd: '4' },
];

const DISPO_OPTIONS = [
  { label: 'Admit — Floor', cmd: 'dispo admit-floor' },
  { label: 'Admit — ICU', cmd: 'dispo admit-icu' },
  { label: 'Discharge', cmd: 'dispo discharge' },
  { label: 'Transfer', cmd: 'dispo transfer' },
];

export default function ActionBar({ sendCommand }) {
  const [mode, setMode] = useState('top');
  const [customInput, setCustomInput] = useState('');
  const inputRef = useRef(null);
  const topInputRef = useRef(null);

  // Auto-focus text inputs when they appear
  useEffect(() => {
    if (mode === 'talk-patient' || mode === 'test' || mode === 'talk-resident') {
      inputRef.current?.focus();
    }
    if (mode === 'top') {
      topInputRef.current?.focus();
    }
  }, [mode]);

  const fire = (cmd) => {
    sendCommand(cmd);
    setMode('top');
    setCustomInput('');
  };

  const back = () => {
    setMode('top');
    setCustomInput('');
  };

  const handleCustomSubmit = (prefix) => {
    if (!customInput.trim()) return;
    fire(`${prefix} ${customInput.trim()}`);
  };

  // Top-level: action buttons + text field for free commands
  if (mode === 'top') {
    return (
      <div className="action-bar">
        <div className="action-buttons">
          <button className="action-btn" onClick={() => setMode('exam')}>Exam</button>
          <button className="action-btn" onClick={() => setMode('test')}>Test</button>
          <button className="action-btn" onClick={() => setMode('talk-patient')}>Talk to Patient</button>
          <button className="action-btn" onClick={() => setMode('talk-resident')}>Talk to Resident</button>
          <button className="action-btn" onClick={() => fire('chart')}>Chart</button>
          <button className="action-btn" onClick={() => fire('status')}>Status</button>
          <button className="action-btn action-btn-dispo" onClick={() => setMode('disposition')}>Disposition</button>
        </div>
        <div className="action-input-row">
          <span className="input-prompt">{'>'}</span>
          <input
            ref={topInputRef}
            className="input-field"
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && customInput.trim()) {
                fire(customInput.trim());
              }
            }}
            placeholder="or type any command…"
            autoComplete="off"
            spellCheck="false"
          />
        </div>
      </div>
    );
  }

  // Exam submenu
  if (mode === 'exam') {
    return (
      <div className="action-bar">
        <div className="action-label">EXAM — pick body area:</div>
        <div className="action-buttons">
          {EXAM_PARTS.map(part => (
            <button key={part} className="action-btn sub" onClick={() => fire(`exam ${part.toLowerCase()}`)}>
              {part}
            </button>
          ))}
          <button className="action-btn back" onClick={back}>← Back</button>
        </div>
        <div className="action-input-row">
          <input
            ref={inputRef}
            className="input-field"
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCustomSubmit('exam'); }}
            placeholder="or type specific area…"
            autoComplete="off"
          />
        </div>
      </div>
    );
  }

  // Test submenu
  if (mode === 'test') {
    return (
      <div className="action-bar">
        <div className="action-label">ORDER TEST:</div>
        <div className="action-buttons">
          {COMMON_TESTS.map(t => (
            <button key={t} className="action-btn sub" onClick={() => fire(`test ${t.toLowerCase()}`)}>
              {t}
            </button>
          ))}
          <button className="action-btn back" onClick={back}>← Back</button>
        </div>
        <div className="action-input-row">
          <input
            ref={inputRef}
            className="input-field"
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCustomSubmit('test'); }}
            placeholder="or type custom test…"
            autoComplete="off"
          />
        </div>
      </div>
    );
  }

  // Talk to patient
  if (mode === 'talk-patient') {
    return (
      <div className="action-bar">
        <div className="action-label">TALK TO PATIENT:</div>
        <div className="action-input-row wide">
          <input
            ref={inputRef}
            className="input-field"
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCustomSubmit(''); }}
            placeholder="What do you want to say or ask?"
            autoComplete="off"
          />
          <button className="action-btn send" onClick={() => handleCustomSubmit('')}>Send</button>
          <button className="action-btn back" onClick={back}>← Back</button>
        </div>
      </div>
    );
  }

  // Talk to resident
  if (mode === 'talk-resident') {
    return (
      <div className="action-bar">
        <div className="action-label">TALK TO RESIDENT:</div>
        <div className="action-buttons">
          {RESIDENT_PRESETS.map(p => (
            <button key={p.label} className="action-btn sub" onClick={() => fire(p.cmd)}>
              {p.label}
            </button>
          ))}
          <button className="action-btn back" onClick={back}>← Back</button>
        </div>
        <div className="action-input-row">
          <input
            ref={inputRef}
            className="input-field"
            value={customInput}
            onChange={e => setCustomInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCustomSubmit('ask'); }}
            placeholder="or ask something specific…"
            autoComplete="off"
          />
        </div>
      </div>
    );
  }

  // Disposition
  if (mode === 'disposition') {
    return (
      <div className="action-bar">
        <div className="action-label">DISPOSITION:</div>
        <div className="action-buttons">
          {DISPO_OPTIONS.map(d => (
            <button key={d.label} className="action-btn sub dispo" onClick={() => fire(d.cmd)}>
              {d.label}
            </button>
          ))}
          <button className="action-btn back" onClick={back}>← Back</button>
        </div>
      </div>
    );
  }

  return null;
}
