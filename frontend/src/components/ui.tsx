import { useEffect, type ReactNode } from "react";

const PATHS = {
  candle: "M12 1.5c2 2.3 2.8 3.9 2.8 5.2a2.8 2.8 0 0 1-5.6 0c0-1.3.8-2.9 2.8-5.2zM8.5 11h7v10.5h-7z",
  close: "M6 6l12 12M18 6L6 18",
  menu: "M4 7h16M4 12h16M4 17h16",
  left: "M15 6l-6 6 6 6",
  right: "M9 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  trash: "M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13",
  up: "M6 15l6-6 6 6",
  down: "M6 9l6 6 6-6",
  shield: "M12 3l7 3v5c0 5-3 8.5-7 10-4-1.5-7-5-7-10V6z",
  hand: "M8 11V5.5a1.5 1.5 0 0 1 3 0V11m0-1V4.5a1.5 1.5 0 0 1 3 0V11m0-.5V6a1.5 1.5 0 0 1 3 0v8a7 7 0 0 1-7 7 6 6 0 0 1-5.2-3L3 14.5a1.5 1.5 0 0 1 2.4-1.8L8 15",
} as const;

export function Icon({ name, size = 18 }: { name: keyof typeof PATHS; size?: number }) {
  const filled = name === "candle";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
      fill={filled ? "currentColor" : "none"} stroke={filled ? "none" : "currentColor"}
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[name]} />
    </svg>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="sb-field">
      <span>{label}</span>
      {children}
      {hint && <small className="sb-hint">{hint}</small>}
    </label>
  );
}

export function Check({ checked, onChange, children, disabled }: {
  checked: boolean; onChange: (v: boolean) => void; children: ReactNode; disabled?: boolean;
}) {
  return (
    <label className="sb-check">
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="sb-seg" role="group">
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Drawer({ open, onClose, title, subtitle, crumbs, children, footer }: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  crumbs?: { label: string; onClick?: () => void }[];
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <>
      <div className="sb-scrim" onClick={onClose} />
      <aside className="sb-drawer" role="dialog" aria-modal="true">
        <div className="sb-drawer-head">
          <div className="sb-grow sb-stack" style={{ gap: 4, flex: 1, minWidth: 0 }}>
            {crumbs && crumbs.length > 0 && (
              <nav className="sb-crumbs">
                {crumbs.map((c, i) => (
                  <span key={i} className="sb-row" style={{ gap: 4 }}>
                    {c.onClick ? <button onClick={c.onClick}>{c.label}</button> : <span>{c.label}</span>}
                    {i < crumbs.length - 1 && <span>›</span>}
                  </span>
                ))}
              </nav>
            )}
            <h2>{title}</h2>
            {subtitle && <p className="sb-hint">{subtitle}</p>}
          </div>
          <button className="sb-btn sb-btn-ghost sb-icon-btn" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>
        <div className="sb-drawer-body">{children}</div>
        {footer && <div className="sb-drawer-head" style={{ borderTop: "1px solid var(--border)", borderBottom: 0 }}>{footer}</div>}
      </aside>
    </>
  );
}

export function SaveBar({ dirty, saving, error, onSave, onReset, label = "Save" }: {
  dirty: boolean; saving: boolean; error?: string; onSave: () => void; onReset?: () => void; label?: string;
}) {
  return (
    <div className="sb-row">
      {error && <span className="sb-error">{error}</span>}
      <span className="sb-spacer" />
      {onReset && <button className="sb-btn" disabled={!dirty || saving} onClick={onReset}>Discard</button>}
      <button className="sb-btn sb-btn-primary" disabled={!dirty || saving} onClick={onSave}>
        {saving ? "Saving…" : label}
      </button>
    </div>
  );
}

export function Loading() {
  return <div className="sb-empty">Loading…</div>;
}
