import { useEffect, useRef, useState } from 'react';
import { FaCloudDownloadAlt } from 'react-icons/fa';
import { API_BASE } from '../config';

/**
 * The backend runs on a free Render instance that sleeps after inactivity and
 * needs 30-90 s to wake. Instead of a blank screen or random timeouts, say so.
 * Shows only when /health has not answered within 3 s of app start, and hides
 * as soon as it does. Lists stay usable from the offline cache meanwhile.
 */
export default function ColdStartBanner() {
  const [waking, setWaking] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const done = useRef(false);

  useEffect(() => {
    const started = Date.now();
    let cancelled = false;
    const showTimer = window.setTimeout(() => { if (!done.current) setWaking(true); }, 3000);
    const tick = window.setInterval(() => setSeconds(Math.round((Date.now() - started) / 1000)), 1000);

    const probe = async () => {
      while (!cancelled) {
        try {
          const ctrl = new AbortController();
          const t = window.setTimeout(() => ctrl.abort(), 15000);
          const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal, cache: 'no-store' });
          window.clearTimeout(t);
          if (res.ok) { done.current = true; setWaking(false); return; }
        } catch { /* keep probing */ }
        await new Promise(r => setTimeout(r, 4000));
      }
    };
    probe();
    return () => { cancelled = true; window.clearTimeout(showTimer); window.clearInterval(tick); };
  }, []);

  if (!waking) return null;
  return (
    <div role="status" style={{
      display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px',
      background: 'var(--amber-soft)', color: 'var(--amber-strong)', borderBottom: '1px solid var(--amber)',
      fontSize: '13px', fontWeight: 600,
    }}>
      <FaCloudDownloadAlt />
      <span>Despertant el servidor… ({seconds}s). Pot trigar fins a un minut la primera vegada; mentrestant veus les dades desades al dispositiu.</span>
    </div>
  );
}
