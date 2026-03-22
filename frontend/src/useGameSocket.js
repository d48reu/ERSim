/**
 * useGameSocket — manages the WebSocket connection to the ERSim API.
 *
 * Returns:
 *   messages     — array of {id, type, text, source, ts}
 *   status       — "idle" | "connecting" | "connected" | "disconnected"
 *   sessionData  — { session_id, bays } from POST /session
 *   sendCommand  — (text: string) => void
 *   startSession — () => void
 */

import { useState, useRef, useCallback, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || '';

let _msgId = 0;
const nextId = () => ++_msgId;

export function useGameSocket() {
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState('idle');
  const [sessionData, setSessionData] = useState(null);
  const [pendingDecisions, setPendingDecisions] = useState([]);
  const [setupProgress, setSetupProgress] = useState(null);
  const [shiftEndedData, setShiftEndedData] = useState(null);
  const wsRef = useRef(null);
  const sessionIdRef = useRef(null);

  const addMessage = useCallback((type, text, source = 'system') => {
    if (!text?.trim()) return;
    setMessages(prev => [...prev, {
      id: nextId(),
      type,
      text: text.trim(),
      source,
      ts: new Date().toLocaleTimeString('en-US', { hour12: false }),
    }]);
  }, []);

  const addMessageIfNew = useCallback((type, text, source = 'system') => {
    if (!text?.trim()) return;
    setMessages(prev => {
      if (prev.at(-1)?.text === text.trim()) return prev;
      return [...prev, {
        id: nextId(),
        type,
        text: text.trim(),
        source,
        ts: new Date().toLocaleTimeString('en-US', { hour12: false }),
      }];
    });
  }, []);

  const clearSetupMessages = useCallback(() => {
    setMessages(prev => prev.filter(msg => {
      const text = msg.text || '';
      if (text.includes('Setting up shift — generating resident assessments...')) return false;
      if (text.includes('Building resident reads')) return false;
      return true;
    }));
  }, []);

  const connect = useCallback((sessionId) => {
    const wsUrl = `${API.replace(/^http/, 'ws')}/session/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    setStatus('connecting');

    ws.onopen = () => setStatus('connected');

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const { type, text, source, summary, bays, feedback_context } = msg;
        if (type === 'shift_ended') {
          addMessageIfNew('shift_ended', summary || text, 'system');
          setShiftEndedData({
            summary: summary || text || '',
            feedbackContext: feedback_context || null,
          });
          setPendingDecisions([]);
          setStatus('disconnected');
        } else if (type === 'setup_complete') {
          // Update session data with live bay info
          if (bays) {
            setSessionData(prev => ({ ...prev, bays, status: 'ready' }));
          }
          setSetupProgress(null);
          clearSetupMessages();
        } else if (type === 'setup_progress') {
          setSetupProgress(prev => ({
            completed: msg.completed || 0,
            total: msg.total || 0,
            currentBay: msg.current_bay || null,
            doneBays: msg.current_bay
              ? [...new Set([...(prev?.doneBays || []), msg.current_bay])]
              : (prev?.doneBays || []),
          }));
        } else if (type === 'result') {
          addMessage('result', text, 'result');
        } else if (type === 'autonomous') {
          addMessage('autonomous', text, 'resident');
        } else if (type === 'warning') {
          addMessage('warning', text, 'warning');
        } else if (type === 'cross_bay_decision') {
          // Queue for notification banner — don't dump into the log
          setPendingDecisions(prev => [...prev, {
            id: nextId(),
            bay_id: msg.bay_id,
            resident_name: msg.resident_name,
            patient_name: msg.patient_name,
            text: msg.text,
            options: msg.options,
          }]);
        } else if (type === 'error') {
          addMessage('error', text, 'error');
        } else if (type === 'message') {
          addMessage('message', text, source || 'system');
        }
      } catch {
        addMessage('message', e.data, 'system');
      }
    };

    ws.onerror = () => addMessage('error', 'Connection error.', 'error');
    ws.onclose = () => {
      setPendingDecisions([]);
      setStatus('disconnected');
      wsRef.current = null;
    };
  }, [addMessage, addMessageIfNew, clearSetupMessages]);

  const startSession = useCallback(async () => {
    setStatus('connecting');
    setMessages([]);
    setPendingDecisions([]);
    setSetupProgress(null);
    setSessionData(null);
    setShiftEndedData(null);
    try {
      const res = await fetch(`${API}/session`, { method: 'POST' });
      const data = await res.json();
      sessionIdRef.current = data.session_id;
      setSessionData(data);
      addMessage('system', data.start_text, 'system');
      connect(data.session_id);
    } catch (err) {
      addMessage('error', `Failed to start session: ${err.message}`, 'error');
      setStatus('idle');
    }
  }, [connect, addMessage]);

  const sendCommand = useCallback((text) => {
    if (!text?.trim()) return;
    // Echo the command
    addMessage('command', text, 'command');
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: text }));
    }
  }, [addMessage]);

  // Silent send — no echo, response marked silent (sidebar-only)
  const sendSilent = useCallback((text) => {
    if (!text?.trim()) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: text, silent: true }));
    }
  }, []);

  const dismissDecision = useCallback((decisionId) => {
    setPendingDecisions(prev => prev.filter(d => d.id !== decisionId));
  }, []);

  // Cleanup on unmount
  useEffect(() => () => wsRef.current?.close(), []);

  return {
    messages,
    status,
    sessionData,
    setupProgress,
    shiftEndedData,
    sendCommand,
    sendSilent,
    startSession,
    pendingDecisions,
    dismissDecision,
  };
}
