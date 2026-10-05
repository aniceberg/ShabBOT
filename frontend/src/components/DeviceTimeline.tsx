import { friendlyName } from "../hass";
import { time, ANCHOR_LABEL } from "../format";
import type { PlannedAction } from "../types";

const MARKERS = ["candle_lighting", "sunset", "tzeit", "midnight", "sunrise", "chatzot", "block_start", "block_end"];

interface Row {
  entity_id: string;
  bars: { start: number; end: number; state: string; label: string; color: string; disabled: boolean }[];
}

/** Gantt-style view of when each device is on/off within a window, with zmanim markers. */
export function DeviceTimeline({ actions, color, anchors, onEntityClick, range }: {
  actions: PlannedAction[];
  color: string;
  anchors?: Record<string, string>;
  onEntityClick?: (entityId: string) => void;
  /** Fixed time window to draw (defaults to the span of the actions). */
  range?: [string, string];
}) {
  const valid = actions.filter((a) => a.start && a.end && !a.error);
  if (valid.length === 0) return <p className="sb-hint">No scheduled device changes.</p>;
  const t0 = range ? +new Date(range[0]) : Math.min(...valid.map((a) => +new Date(a.start!)));
  const t1 = range ? +new Date(range[1]) : Math.max(...valid.map((a) => +new Date(a.end!)));
  const pad = Math.max((t1 - t0) * 0.04, 10 * 60_000);
  const lo = t0 - pad;
  const hi = t1 + pad;
  const pct = (t: number) => `${(((t - lo) / (hi - lo)) * 100).toFixed(3)}%`;

  const rows = new Map<string, Row>();
  for (const a of valid) {
    const row = rows.get(a.entity_id) ?? { entity_id: a.entity_id, bars: [] };
    row.bars.push({
      start: +new Date(a.start!),
      end: +new Date(a.end!),
      state: a.state,
      label: `${a.state === "on" ? "On" : "Off"} ${time(a.start)}–${time(a.end)}${a.attrs.brightness ? ` · ${a.attrs.brightness}%` : ""}`,
      color,
      disabled: a.disabled,
    });
    rows.set(a.entity_id, row);
  }

  const markers = Object.entries(anchors ?? {})
    .filter(([k]) => MARKERS.includes(k))
    .map(([k, v]) => ({ key: k, t: +new Date(v) }))
    .filter((m) => m.t >= lo && m.t <= hi)
    .sort((a, b) => a.t - b.t);
  // Only label markers far enough apart to stay readable; the dashed lines still show for all.
  const labelled = new Set<string>();
  let lastLabel = -Infinity;
  for (const m of markers) {
    if ((m.t - lastLabel) / (hi - lo) > 0.14) {
      labelled.add(m.key);
      lastLabel = m.t;
    }
  }

  return (
    <div className="sb-gantt">
      {[...rows.values()].map((row) => (
        <div className="sb-gantt-row" key={row.entity_id}>
          <div className="sb-gantt-label" title={row.entity_id}>
            {onEntityClick ? (
              <button className="sb-chip" style={{ fontSize: 12 }} onClick={() => onEntityClick(row.entity_id)}>
                {friendlyName(row.entity_id)}
              </button>
            ) : friendlyName(row.entity_id)}
          </div>
          <div className="sb-gantt-track">
            {markers.map((m) => <div key={m.key} className="sb-gantt-marker" style={{ left: pct(m.t) }} />)}
            {row.bars.map((b, i) => (
              <div key={i} title={b.label}
                className={`sb-gantt-bar ${b.state === "off" ? "sb-off" : ""}`}
                style={{
                  left: pct(b.start), width: `calc(${pct(b.end)} - ${pct(b.start)})`,
                  background: b.state === "on" ? b.color : undefined, opacity: b.disabled ? 0.3 : undefined,
                }}>
                {b.state === "on" ? b.label : ""}
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="sb-gantt-row" style={{ minHeight: 34 }}>
        <div />
        <div style={{ position: "relative", height: 34 }}>
          {markers.filter((m) => labelled.has(m.key)).map((m) => (
            <div key={m.key} className="sb-gantt-tick" style={{ left: pct(m.t), color: "var(--candle)" }}>
              {ANCHOR_LABEL[m.key]?.split(" (")[0] ?? m.key}<br />{time(new Date(m.t))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
