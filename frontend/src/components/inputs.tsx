import { useEffect, useId, useMemo, useState } from "react";
import { callWS, CONTROLLABLE, shallowEqual, useHassSelector } from "../hass";
import { ANCHOR_CHIP, ANCHOR_LABEL, dayTime, describeExpr } from "../format";
import type { Part } from "../types";

/** Entity picker over controllable entities, with friendly names. */
export function EntityPicker({ value, onChange, domains = CONTROLLABLE, placeholder = "Choose a device…" }: {
  value: string; onChange: (v: string) => void; domains?: string[]; placeholder?: string;
}) {
  const listId = useId();
  const options = useHassSelector(
    (h) =>
      Object.fromEntries(
        Object.values(h.states)
          .filter((s) => domains.includes(s.entity_id.split(".")[0]))
          .map((s) => [s.entity_id, (s.attributes.friendly_name as string) || s.entity_id]),
      ) as Record<string, string>,
    shallowEqual,
  );
  const sorted = useMemo(() => Object.entries(options).sort((a, b) => a[1].localeCompare(b[1])), [options]);
  const known = value in options;
  return (
    <div className="sb-stack" style={{ gap: 2 }}>
      <input className={`sb-input ${value && !known ? "sb-invalid" : ""}`} list={listId} value={value}
        placeholder={placeholder} onChange={(e) => onChange(e.target.value.trim())} />
      <datalist id={listId}>
        {sorted.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
      </datalist>
      <small className="sb-preview">{known ? options[value] : value ? "Not found in Home Assistant" : ""}</small>
    </div>
  );
}

const QUICK = ["candle_lighting", "sunset", "tzeit", "midnight", "sunrise", "chatzot", "havdalah"];

/** Time expression input with live preview against the next matching Shabbat/Yom Tov. */
export function ExprInput({ value, onChange, part, slotKey, resolved }: {
  value: string; onChange: (v: string) => void; part: Part; slotKey?: string;
  /** Time the whole row resolves to (e.g. an end read as the next morning); overrides the single-field preview. */
  resolved?: string | null;
}) {
  const [preview, setPreview] = useState<{ time?: string; error?: string; title?: string }>({});
  useEffect(() => {
    if (!value.trim()) {
      setPreview({ error: "Required" });
      return;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      callWS<{ time?: string; error?: string; title?: string }>({
        type: "shabbot/preview", expr: value, ...(slotKey ? { key: slotKey } : { part }),
      }).then((r) => !cancelled && setPreview(r), (e) => !cancelled && setPreview({ error: String(e?.message ?? e) }));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [value, part, slotKey]);
  const quick = QUICK;
  const shown = resolved ?? preview.time;
  return (
    <div>
      <input className={`sb-input sb-mono ${preview.error ? "sb-invalid" : ""}`} value={value}
        onChange={(e) => onChange(e.target.value)} placeholder="e.g. sunset+18m or 11:45pm" spellCheck={false} />
      <div className="sb-preview" title={preview.title}>
        {preview.error ? <span className="sb-error">{preview.error}</span>
          : shown ? `${describeExpr(value) ? `${describeExpr(value)} ` : ""}→ ${dayTime(shown)}` : ""}
      </div>
      <details>
        <summary className="sb-hint" style={{ cursor: "pointer", fontSize: 11 }}>Insert time</summary>
        <div className="sb-chips">
          {quick.map((q) => (
            <button key={q} type="button" className="sb-chip" title={`${ANCHOR_LABEL[q]} (${q})`} onClick={() => onChange(q)}>
              {ANCHOR_CHIP[q] ?? q}
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}

/** Routine dropdown for one part; `specials` adds entries like "Use default rules" (null) or "Nothing" ("none"). */
export function RoutineSelect({ value, onChange, routines, part, specials }: {
  value: string | null;
  onChange: (v: string | null) => void;
  routines: { id: string; name: string; part: Part }[];
  part: Part;
  specials: { value: string | null; label: string }[];
}) {
  const enc = (v: string | null) => (v === null ? "__null__" : v);
  return (
    <select className="sb-select" value={enc(value)}
      onChange={(e) => onChange(e.target.value === "__null__" ? null : e.target.value)}>
      {specials.map((s) => <option key={enc(s.value)} value={enc(s.value)}>{s.label}</option>)}
      {routines.filter((r) => r.part === part).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
    </select>
  );
}
