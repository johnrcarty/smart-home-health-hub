import React, { useEffect, useRef, useState } from 'react';
import config from '../../config';

const COMMON_BAUD_RATES = [19200, 9600, 38400, 57600, 115200, 4800, 2400];

export default function SerialSettings() {
  const [baudRate, setBaudRate] = useState(19200);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [autoDetecting, setAutoDetecting] = useState(false);
  const [serialActive, setSerialActive] = useState(false);
  const [log, setLog] = useState([]); // last ~30
  const wsRef = useRef(null);
  const autoDetectStopRef = useRef(false);

  // Build WS URL from apiUrl
  const buildWsUrl = () => {
    try {
      const url = new URL(config.apiUrl);
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      url.pathname = '/ws/sensors';
      return url.toString();
    } catch {
      // Fallback
      return (config.apiUrl || '').replace(/^http/, 'ws') + '/ws/sensors';
    }
  };

  useEffect(() => {
    // Load current setting & status
    const load = async () => {
      try {
        setError(null);
        const [baudRes, statusRes, logRes] = await Promise.all([
          fetch(`${config.apiUrl}/api/settings/baud_rate`),
          fetch(`${config.apiUrl}/api/serial/status`),
          fetch(`${config.apiUrl}/api/serial/log`)
        ]);
        if (baudRes.ok) {
          const br = await baudRes.json();
          const val = br?.value ?? 19200;
          setBaudRate(Number(val));
        }
        if (statusRes.ok) {
          const st = await statusRes.json();
          setSerialActive(!!st.serial_active);
        }
        if (logRes.ok) {
          const data = await logRes.json();
          if (Array.isArray(data.lines)) setLog(data.lines.slice(-30));
        }
      } catch (e) {
        setError('Failed to load serial info');
      }
    };
    load();

    // Open websocket
    const ws = new WebSocket(buildWsUrl());
    wsRef.current = ws;
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg?.type === 'serial_raw' && typeof msg.line === 'string') {
          setLog(prev => {
            const next = [...prev, msg.line];
            return next.slice(-30);
          });
        } else if (msg?.type === 'sensor_update') {
          // optionally update serial active if included later
        }
      } catch {}
    };
    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => {
      try { ws.close(); } catch {}
      autoDetectStopRef.current = true;
    };
  }, []);

  const saveBaudRate = async (value) => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const payload = { settings: { baud_rate: Number(value) } };
      const res = await fetch(`${config.apiUrl}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Failed to save');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (e) {
      setError('Failed to save baud rate');
    } finally {
      setSaving(false);
    }
  };

  const validateLine = (line) => {
    if (!line || typeof line !== 'string') return false;
    const parts = line.trim().split(/\s+/);
    return parts.length >= 5; // matches serial_reader minimal requirement
  };

  const autoDetect = async () => {
    setAutoDetecting(true);
    setError(null);
    autoDetectStopRef.current = false;

    const original = baudRate;
    let detected = null;

    try {
      for (const rate of COMMON_BAUD_RATES) {
        if (autoDetectStopRef.current) break;
        setBaudRate(rate);
        await saveBaudRate(rate);
        // Wait for data to arrive at this rate
        const start = Date.now();
        let goodCount = 0;
        while (Date.now() - start < 3500) {
          await new Promise(r => setTimeout(r, 250));
          const lastFew = log.slice(-5);
          goodCount = lastFew.filter(validateLine).length;
          if (goodCount >= 3) {
            detected = rate;
            break;
          }
        }
        if (detected) break;
      }

      if (detected) {
        setBaudRate(detected);
        setSuccess(true);
        setTimeout(() => setSuccess(false), 2500);
      } else {
        setError('Auto-detect could not determine a working baud rate. Try selecting manually.');
        // Restore original selection visually (setting will remain last tried)
        setBaudRate(original);
        await saveBaudRate(original);
      }
    } catch (e) {
      setError('Auto-detect failed');
    } finally {
      setAutoDetecting(false);
    }
  };

  return (
    <div style={{ background: 'rgba(20,24,32,0.8)', borderRadius: 12, padding: 16, border: '1px solid #4a5568' }}>
      <h3 style={{ color: '#fff', margin: 0, marginBottom: 12 }}>Serial Settings</h3>

      {error && (
        <div style={{ background: '#fed7d7', color: '#9b2c2c', padding: '8px 10px', borderRadius: 6, marginBottom: 10 }}>{error}</div>
      )}
      {success && (
        <div style={{ background: '#c6f6d5', color: '#276749', padding: '8px 10px', borderRadius: 6, marginBottom: 10 }}>Saved</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }}>
        <div>
          <label style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 6 }}>Baud Rate</label>
          <select
            value={baudRate}
            onChange={(e) => setBaudRate(Number(e.target.value))}
            disabled={saving || autoDetecting}
            style={{ width: '100%', padding: '10px 12px', background: '#2d3748', color: '#fff', border: '1px solid #4a5568', borderRadius: 6 }}
          >
            {COMMON_BAUD_RATES.map(br => (
              <option key={br} value={br}>{br}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <button
            onClick={() => saveBaudRate(baudRate)}
            disabled={saving || autoDetecting}
            style={{ background: '#007bff', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 16px', cursor: saving? 'not-allowed':'pointer' }}
          >{saving? 'Saving…' : 'Save'}</button>
          <button
            onClick={autoDetect}
            disabled={autoDetecting || saving}
            style={{ background: '#4a5568', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 16px', cursor: autoDetecting? 'not-allowed':'pointer' }}
          >{autoDetecting? 'Auto-detecting…' : 'Auto-detect'}</button>
        </div>
      </div>

      <div style={{ marginBottom: 12, color: '#cbd5e0', fontSize: 13 }}>
        <strong style={{ color: '#fff' }}>Tip:</strong> Use Auto-detect to try common baud rates automatically. When a working rate is found, recent serial messages will appear below.
      </div>

      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, padding: 8, maxHeight: 240, overflowY: 'auto' }}>
        {log.length === 0 ? (
          <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>No serial data yet…</div>
        ) : (
          log.map((line, idx) => (
            <pre key={idx} style={{ margin: 0, color: '#e2e8f0', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>{line}</pre>
          ))
        )}
      </div>

      <div style={{ marginTop: 8, color: serialActive ? '#48bb78' : '#f6ad55', fontSize: 12 }}>
        Status: {serialActive ? 'Connected' : 'Not connected'}
      </div>
    </div>
  );
}
