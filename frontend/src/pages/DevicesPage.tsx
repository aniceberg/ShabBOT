import { useEffect, useRef, useState } from "react";
import { callWS, friendlyName, getHass } from "../hass";
import { errorMessage, invalidateAll, useConfig, useStatus } from "../api";
import { Check, Drawer, Field, Icon, Loading, SaveBar } from "../components/ui";
import { EntityPicker } from "../components/inputs";
import { dayTime, time } from "../format";
import type { DeviceConfig, EntityStatus, LearnedEvent, Matcher } from "../types";

const DETECTOR_HELP: Record<string, string> = {
  none: "Only the Override button here (or the shabbot.start_override action) pauses protection.",
  event: "A button event starts and ends the override, e.g. a Zooz triple-tap or a Lutron Pico press. Use the Z-Wave preset or Learn.",
  flip_pattern: "For switches that only report on/off (Caséta, Kasa, Wemo): flipping the switch several times quickly starts an override. The same pattern ends it.",
  persistence: "For on/off-only switches: if someone keeps undoing ShabBOT's correction, the last time counts as intentional.",
};

export function DevicesPage() {
  const status = useStatus();
  const config = useConfig();
  const [open, setOpen] = useState<string | null>(null);
  const [adding, setAdding] = useState("");
  if (!status.data || !config.data) return <Loading />;
  const rows = status.data.entities;

  const addDevice = async () => {
    if (!adding) return;
    await callWS({ type: "shabbot/device/save", entity_id: adding, device: { protect: true } });
    invalidateAll();
    setOpen(adding);
    setAdding("");
  };

  return (
    <div className="sb-stack">
      <div className="sb-card sb-card-pad sb-stack">
        <div>
          <h3 className="sb-section-title">Devices</h3>
          <p className="sb-hint">
            Every device used in a routine is listed here. During Shabbat/Yom Tov, protected devices are put back if they
            change unexpectedly (checked on every change and once a minute).
          </p>
        </div>
        <div className="sb-scroll-x">
          <table className="sb-table">
            <thead>
              <tr><th>Device</th><th>Now</th><th>Should be</th><th>Protection</th><th>Override gesture</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((r) => <DeviceRow key={r.entity_id} row={r} cfg={config.data.config.devices[r.entity_id]} onOpen={() => setOpen(r.entity_id)} />)}
              {rows.length === 0 && <tr><td colSpan={6} className="sb-empty">No devices yet. Add them to a routine, or below.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="sb-row" style={{ alignItems: "flex-start" }}>
          <div style={{ flex: 1, maxWidth: 420 }}><EntityPicker value={adding} onChange={setAdding} placeholder="Add a device to configure…" /></div>
          <button className="sb-btn" disabled={!adding} onClick={addDevice}><Icon name="plus" size={16} /> Add</button>
        </div>
      </div>
      {open && (
        <DeviceDrawer entityId={open} row={rows.find((r) => r.entity_id === open)}
          cfg={{ ...config.data.meta.default_device, ...(config.data.config.devices[open] ?? {}) }}
          onClose={() => setOpen(null)} />
      )}
    </div>
  );
}

function DeviceRow({ row, cfg, onOpen }: { row: EntityStatus; cfg?: DeviceConfig; onOpen: () => void }) {
  const detector = cfg?.override?.detector ?? "none";
  return (
    <tr>
      <td>
        <button className="sb-chip" style={{ fontSize: 13 }} onClick={onOpen}>{row.name}</button>
        <div className="sb-hint sb-mono" style={{ fontSize: 11 }}>{row.entity_id}</div>
      </td>
      <td><span className={`sb-badge ${row.state === "on" ? "sb-badge-ok" : ""}`}>{row.state ?? "missing"}</span></td>
      <td>
        {row.desired ? (
          <span className={`sb-badge ${row.in_sync ? "" : "sb-badge-danger"}`} title={row.desired.routine_name}>
            {row.desired.state} until {time(row.desired.end)}
          </span>
        ) : <span className="sb-hint">—</span>}
      </td>
      <td>
        {row.override ? <span className="sb-badge sb-badge-warn">Overridden until {time(row.override.until)}</span>
          : row.paused ? <span className="sb-badge sb-badge-danger">Paused: {row.paused}</span>
          : row.protected ? <span className="sb-badge sb-badge-ok">Protected</span>
          : cfg?.protect === false ? <span className="sb-badge">Off</span>
          : <span className="sb-hint">Not now</span>}
      </td>
      <td className="sb-hint">{{ none: "—", event: cfg?.override?.preset?.startsWith("zwave") ? "Z-Wave multi-tap" : "Button event", flip_pattern: "Quick flips", persistence: "Keeps undoing" }[detector]}</td>
      <td><button className="sb-btn sb-btn-sm" onClick={onOpen}>Configure</button></td>
    </tr>
  );
}

function DeviceDrawer({ entityId, row, cfg, onClose }: {
  entityId: string; row?: EntityStatus; cfg: Required<DeviceConfig>; onClose: () => void;
}) {
  const [draft, setDraft] = useState<Required<DeviceConfig>>(structuredClone(cfg));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [minutes, setMinutes] = useState(String(cfg.override_minutes));
  useEffect(() => setDraft(structuredClone(cfg)), [entityId]); // eslint-disable-line react-hooks/exhaustive-deps
  const ov = draft.override;
  const dirty = JSON.stringify(draft) !== JSON.stringify(cfg);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await callWS({ type: "shabbot/device/save", entity_id: entityId, device: draft });
      invalidateAll();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };
  const zwavePreset = async () => {
    try {
      const preset = await callWS<DeviceConfig["override"]>({ type: "shabbot/device/zwave_preset", entity_id: entityId, taps: 3 });
      setDraft({ ...draft, override: { ...preset!, detector: "event" } });
    } catch (e) {
      setError(errorMessage(e));
    }
  };
  const act = async (type: string, extra: Record<string, unknown> = {}) => {
    await callWS({ type, ...extra });
    invalidateAll();
  };

  return (
    <Drawer open onClose={onClose} title={friendlyName(entityId)} subtitle={entityId}
      footer={<div style={{ flex: 1 }}><SaveBar dirty={dirty} saving={saving} error={error} onSave={save} onReset={() => setDraft(structuredClone(cfg))} /></div>}>
      {row && (
        <div className="sb-card sb-card-pad sb-stack">
          <div className="sb-row">
            <span>Now <strong>{row.state}</strong></span>
            {row.desired && <span className="sb-hint">· should be {row.desired.state} until {dayTime(row.desired.end)} ({row.desired.routine_name})</span>}
          </div>
          <div className="sb-row">
            {row.override ? (
              <>
                <span className="sb-badge sb-badge-warn">Overridden until {time(row.override.until)} · {row.override.reason}</span>
                <button className="sb-btn sb-btn-sm" onClick={() => act("shabbot/override/end", { entity_ids: [entityId] })}>End override</button>
              </>
            ) : (
              <>
                <input className="sb-input" style={{ width: 80 }} type="number" min={1} value={minutes} onChange={(e) => setMinutes(e.target.value)} />
                <span className="sb-hint">min</span>
                <button className="sb-btn sb-btn-sm" onClick={() => act("shabbot/override/start", { entity_ids: [entityId], minutes: Number(minutes) || null })}>
                  <Icon name="hand" size={14} /> Override now
                </button>
              </>
            )}
            {row.paused && (
              <button className="sb-btn sb-btn-sm" onClick={() => act("shabbot/resume", { entity_id: entityId })}>Resume protection ({row.paused})</button>
            )}
          </div>
        </div>
      )}

      <Check checked={draft.protect} onChange={(v) => setDraft({ ...draft, protect: v })}>
        Protect this device during Shabbat/Yom Tov
      </Check>

      <div className="sb-stack">
        <h3 className="sb-section-title">Intentional override</h3>
        <Field label="How someone signals an override">
          <select className="sb-select" value={ov.detector} onChange={(e) => setDraft({ ...draft, override: { ...ov, detector: e.target.value as typeof ov.detector } })}>
            <option value="none">No gesture</option>
            <option value="event">Button event (Z-Wave multi-tap, Pico, remote…)</option>
            <option value="flip_pattern">Flip the switch quickly</option>
            <option value="persistence">Keep turning it back</option>
          </select>
        </Field>
        <p className="sb-hint">{DETECTOR_HELP[ov.detector]}</p>

        {ov.detector === "event" && (
          <div className="sb-stack">
            <div className="sb-row">
              <button className="sb-btn sb-btn-sm" onClick={zwavePreset}>Use Z-Wave triple-tap (up = start, down = end)</button>
            </div>
            <MatcherEditor label="Starts override" value={ov.start ?? null} onChange={(m) => setDraft({ ...draft, override: { ...ov, start: m, preset: null } })} />
            <MatcherEditor label="Ends override early" value={ov.end ?? null} onChange={(m) => setDraft({ ...draft, override: { ...ov, end: m, preset: null } })} />
          </div>
        )}
        {(ov.detector === "flip_pattern" || ov.detector === "persistence") && (
          <div className="sb-grid-2">
            <Field label={ov.detector === "flip_pattern" ? "Number of flips" : "Times undone"}>
              <input className="sb-input" type="number" min={2} max={10} value={ov.count ?? 3}
                onChange={(e) => setDraft({ ...draft, override: { ...ov, count: Number(e.target.value) } })} />
            </Field>
            <Field label="Within (seconds)">
              <input className="sb-input" type="number" min={1} value={ov.window_s ?? (ov.detector === "flip_pattern" ? 6 : 120)}
                onChange={(e) => setDraft({ ...draft, override: { ...ov, window_s: Number(e.target.value) } })} />
            </Field>
          </div>
        )}
        <div className="sb-grid-2">
          <Field label="Override lasts (minutes)">
            <input className="sb-input" type="number" min={1} value={draft.override_minutes}
              onChange={(e) => setDraft({ ...draft, override_minutes: Number(e.target.value) })} />
          </Field>
          <Field label="When it ends">
            <select className="sb-select" value={draft.after_override} onChange={(e) => setDraft({ ...draft, after_override: e.target.value as "reassert" | "next_transition" })}>
              <option value="reassert">Put the device back right away</option>
              <option value="next_transition">Leave it until the next scheduled change</option>
            </select>
          </Field>
        </div>
        <Field label="Also override these devices (same room)">
          <GroupEditor value={draft.override_group} onChange={(g) => setDraft({ ...draft, override_group: g })} exclude={entityId} />
        </Field>
      </div>
    </Drawer>
  );
}

function GroupEditor({ value, onChange, exclude }: { value: string[]; onChange: (v: string[]) => void; exclude: string }) {
  const [adding, setAdding] = useState("");
  return (
    <div className="sb-stack" style={{ gap: 6 }}>
      <div className="sb-chips">
        {value.map((e) => (
          <button key={e} className="sb-chip" onClick={() => onChange(value.filter((x) => x !== e))} title="Remove">{friendlyName(e)} ×</button>
        ))}
        {value.length === 0 && <span className="sb-hint">None</span>}
      </div>
      <div className="sb-row" style={{ alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}><EntityPicker value={adding} onChange={setAdding} /></div>
        <button className="sb-btn sb-btn-sm" disabled={!adding || adding === exclude || value.includes(adding)}
          onClick={() => { onChange([...value, adding]); setAdding(""); }}>Add</button>
      </div>
    </div>
  );
}

function MatcherEditor({ label, value, onChange }: { label: string; value: Matcher | null; onChange: (m: Matcher | null) => void }) {
  const [learning, setLearning] = useState(false);
  const [events, setEvents] = useState<LearnedEvent[]>([]);
  const unsub = useRef<Promise<() => Promise<void>> | null>(null);

  const stop = () => {
    unsub.current?.then((u) => u()).catch(() => undefined);
    unsub.current = null;
    setLearning(false);
  };
  useEffect(() => stop, []);
  const learn = () => {
    setEvents([]);
    setLearning(true);
    unsub.current = getHass().connection.subscribeMessage<LearnedEvent>(
      (ev) => setEvents((prev) => [ev, ...prev].slice(0, 15)), { type: "shabbot/learn" });
  };

  return (
    <div className="sb-card sb-card-pad sb-stack" style={{ gap: 8 }}>
      <div className="sb-row">
        <strong>{label}</strong>
        <span className="sb-spacer" />
        {learning ? <button className="sb-btn sb-btn-sm" onClick={stop}>Stop</button>
          : <button className="sb-btn sb-btn-sm" onClick={learn}>Learn…</button>}
        {value && <button className="sb-btn sb-btn-sm sb-btn-ghost" onClick={() => onChange(null)}>Clear</button>}
      </div>
      {value ? (
        <code className="sb-mono" style={{ fontSize: 12, wordBreak: "break-all" }}>
          {value.event_type} {Object.entries(value.data ?? {}).map(([k, v]) => `${k}=${String(v)}`).join(" ")}
        </code>
      ) : <span className="sb-hint">Not set</span>}
      {learning && (
        <div className="sb-stack" style={{ gap: 4 }}>
          <span className="sb-hint">Press the button or do the gesture now. Events appear here; choose the right one.</span>
          {events.map((ev, i) => (
            <button key={i} className="sb-list-item" style={{ border: "1px solid var(--border)", borderRadius: 8 }}
              onClick={() => { onChange(ev.matcher); stop(); }}>
              <span className="sb-grow sb-mono" style={{ fontSize: 12, wordBreak: "break-all" }}>
                {ev.event_type} {Object.entries(ev.matcher.data ?? {}).map(([k, v]) => `${k}=${String(v)}`).join(" ")}
              </span>
              <span className="sb-hint">{time(ev.time)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
