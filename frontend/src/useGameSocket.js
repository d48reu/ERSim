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

  const connect = useCallback((sessionId) => {
    const wsUrl = `${API.replace(/^http/, 'ws')}/session/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    setStatus('connecting');

    ws.onopen = () => setStatus('connected');

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const { type, text, source, summary } = msg;
        if (type === 'shift_ended') {
          addMessage('shift_ended', summary || text, 'system');
          setStatus('disconnected');
        } else if (type === 'result') {
          addMessage('result', text, 'result');
        } else if (type === 'autonomous') {
          addMessage('autonomous', text, 'resident');
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
      setStatus('disconnected');
      wsRef.current = null;
    };
  }, [addMessage]);

  const startSession = useCallback(async () => {
    setStatus('connecting');
    setMessages([]);
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

  // Cleanup on unmount
  useEffect(() => () => wsRef.current?.close(), []);

  return { messages, status, sessionData, sendCommand, startSession };
}
