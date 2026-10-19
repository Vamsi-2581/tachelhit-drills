import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { FaChevronDown } from 'react-icons/fa';

export interface AiTool {
  key: string;
  icon: ReactNode;
  title: string;
  description: string;
  run: () => void;
  disabled?: boolean;
}

// One trigger per drill row that opens (on hover or click) a list of the AI tools,
// each with a one-line explanation, instead of a row of six cryptic buttons.
// The panel is portaled to <body> so the grid row does not clip it.
export default function AiToolsMenu({ tools, busy }: { tools: AiTool[]; busy?: boolean }) {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number; up: boolean }>({ top: 0, left: 0, up: false });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<number | null>(null);

  const place = () => {
    const r = triggerRef.current?.getBoundingClientRect();
    if (!r) return;
    const up = window.innerHeight - r.bottom < 360;
    setPos({ top: up ? r.top - 6 : r.bottom + 6, left: Math.min(r.left, window.innerWidth - 340), up });
  };
  const show = () => { if (closeTimer.current) window.clearTimeout(closeTimer.current); place(); setOpen(true); };
  const hide = () => { if (pinned) return; closeTimer.current = window.setTimeout(() => setOpen(false), 220); };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); setPinned(false); } };
    const onDown = (e: MouseEvent) => {
      if (triggerRef.current?.contains(e.target as Node)) return;
      if ((e.target as HTMLElement).closest?.('[data-ai-tools-panel]')) return;
      setOpen(false); setPinned(false);
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('mousedown', onDown);
    window.addEventListener('scroll', place, true);
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('mousedown', onDown); window.removeEventListener('scroll', place, true); };
  }, [open, pinned]);

  return (
    <>
      <button
        ref={triggerRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onClick={() => { if (open && pinned) { setOpen(false); setPinned(false); } else { show(); setPinned(true); } }}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Eines d'IA per a aquest drill"
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 10px', fontSize: '12px', fontWeight: 700,
          background: open ? 'var(--brand-gradient-soft)' : 'var(--surface-2)', color: open ? 'var(--brand-1)' : 'var(--text-soft)',
          border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', cursor: 'pointer', whiteSpace: 'nowrap' }}
      >
        ✨ Eines IA <FaChevronDown size={10} />
      </button>
      {open && createPortal(
        <div
          data-ai-tools-panel
          role="menu"
          onMouseEnter={show}
          onMouseLeave={hide}
          style={{ position: 'fixed', top: pos.up ? undefined : pos.top, bottom: pos.up ? window.innerHeight - pos.top : undefined, left: pos.left, zIndex: 20000,
            width: '330px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-lg)', padding: '6px' }}
        >
          <div style={{ padding: '6px 10px 8px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Què pot fer la IA amb aquest drill
          </div>
          {tools.map(t => (
            <button
              key={t.key}
              role="menuitem"
              disabled={busy || t.disabled}
              onClick={() => { setOpen(false); setPinned(false); t.run(); }}
              style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', width: '100%', textAlign: 'left', padding: '8px 10px',
                background: 'transparent', border: 'none', borderRadius: 'var(--r-md)', cursor: busy || t.disabled ? 'not-allowed' : 'pointer', opacity: busy || t.disabled ? 0.45 : 1 }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-2)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <span style={{ flexShrink: 0, width: '26px', height: '26px', borderRadius: 'var(--r-sm)', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px' }}>{t.icon}</span>
              <span style={{ minWidth: 0 }}>
                <span style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>{t.title}</span>
                <span style={{ display: 'block', fontSize: '12px', color: 'var(--text-soft)', lineHeight: 1.35 }}>{t.description}</span>
              </span>
            </button>
          ))}
        </div>,
        document.body
      )}
    </>
  );
}
