import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useDraft } from "../useDraft";
import { callWS, shallowEqual, useHassSelector } from "../hass";
import { errorMessage, invalidateAll, useConfig } from "../api";
import { Check, Field, Loading, SaveBar, Segmented } from "../components/ui";
import { EntityMultiPicker, ExprInput } from "../components/inputs";
import { dateShort, dayTime, time } from "../format";
import type { Nusach, OmerConfig, OmerNight, OmerVoice } from "../types";

const NUSACH_OPTIONS: { value: Nusach; label: string; hint: string }[] = [
  { value: "edot_hamizrach", label: "Edot Hamizrach", hint: "“לָעֹמֶר” right after the days: הַיּוֹם שְׁמוֹנָה יָמִים לָעֹמֶר שֶׁהֵם שָׁבוּעַ אֶחָד וְיוֹם אֶחָד" },
  { value: "sefard", label: "Sefard / Chabad", hint: "“לָעֹמֶר” at the end, after the weeks: …שֶׁהֵם שָׁבוּעַ אֶחָד וְיוֹם אֶחָד לָעֹמֶר" },
  { value: "ashkenaz", label: "Ashkenaz", hint: "“לָעֹמֶר” (or “בָּעֹמֶר”, the Rema's wording) at the end, after the weeks." },
];
const OMER_QUICK = ["sunset", "tzeit", "midnight"];

interface Provider {
  engine_id: string;
  name?: string | null;
  supported_languages?: string[];
}

const isHebrew = (lang: string) => /^(he|iw)([-_]|$)/i.test(lang);
const isEnglish = (lang: string) => /^en([-_]|$)/i.test(lang);

/** Text-to-speech engines in Home Assistant (both TTS entities and older engines). */
function useEngines() {
  return useQuery({
    queryKey: ["tts-engines"],
    queryFn: () => callWS<{ providers: Provider[] }>({ type: "tts/engine/list" }).then((r) => r.providers),
    staleTime: 300_000,
  });
}

function useVoices(engineId: string, language: string | null) {
  return useQuery({
    queryKey: ["tts-voices", engineId, language],
    queryFn: () => callWS<{ voices: { voice_id: string; name: string }[] | null }>({
      type: "tts/engine/voices", engine_id: engineId, language,
    }).then((r) => r.voices ?? [], () => []),
    enabled: Boolean(engineId && language),
    staleTime: 300_000,
  });
}

export function OmerPage() {
  const { data } = useConfig();
  const [draft, setDraft, dirty, reset] = useDraft<OmerConfig>(data?.config.omer);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [shown, setShown] = useState<number | null>(null);
  const [testNote, setTestNote] = useState("");
  const dryRun = Boolean(data?.config.settings.dry_run);

  const draftKey = JSON.stringify(draft ?? null);
  const season = useQuery({
    queryKey: ["omer-season", draftKey],
    queryFn: () => callWS<{ nights: OmerNight[]; tonight: OmerNight | null; next: OmerNight | null }>({
      type: "shabbot/omer/season", ...(draft ? { omer: draft } : {}),
    }),
    enabled: Boolean(draft),
    placeholderData: (prev) => prev,
    retry: 0,
  });

  if (!data || !draft) return <Loading />;
  const set = <K extends keyof OmerConfig>(k: K, v: OmerConfig[K]) => setDraft({ ...draft, [k]: v });
  const wantLang = draft.style === "simple" && draft.simple_language === "en" ? "en" : "he";
  const nights = season.data?.nights ?? [];
  const tonight = season.data?.tonight;
  const selected = nights.find((n) => n.night === (shown ?? tonight?.night ?? nights.find((x) => x.time && new Date(x.time) > new Date())?.night ?? 1));

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      setDraft(await callWS<OmerConfig>({ type: "shabbot/omer/save", omer: draft }));
      invalidateAll();
      season.refetch();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };
  const test = async () => {
    setTestNote("");
    try {
      const r = await callWS<{ night: number }>({ type: "shabbot/omer/test", omer: draft, night: selected?.night });
      setTestNote(`Playing night ${r.night} now. See Activity if nothing is heard.`);
    } catch (e) {
      setTestNote(`Test failed: ${errorMessage(e)}`);
    }
  };
  const setNight = (evening: string, choice: string) => {
    const next = { ...draft.nights };
    if (choice === "") delete next[evening];
    else next[evening] = choice as "announce" | "skip";
    set("nights", next);
  };
  const sefirahDefault = draft.nusach !== "ashkenaz";

  return (
    <div className="sb-stack">
      <div className="sb-card sb-card-pad sb-stack">
        <div>
          <h3 className="sb-section-title">Sefirat Haomer reminder</h3>
          <p className="sb-hint">
            Every night of the Omer, ShabBOT announces the count on your speakers at the time you choose. The night is
            worked out from the Hebrew calendar, so it is always the right count for that evening.
          </p>
        </div>
        <Check checked={draft.enabled} onChange={(v) => set("enabled", v)}>Announce the Omer every night</Check>
        {draft.enabled && dryRun && (
          <div className="sb-banner">Dry run is on: the reminder is only written to Activity until you go live.</div>
        )}
        {season.data?.next && draft.enabled && !dirty && (
          <p className="sb-hint">Next: night {season.data.next.night}, {dayTime(season.data.next.time)} ({dateShort(season.data.next.evening + "T12:00")} evening).</p>
        )}
      </div>

      <div className="sb-card sb-card-pad sb-stack">
        <h3 className="sb-section-title">What to say</h3>
        <Field label="Read-out">
          <Segmented value={draft.style} onChange={(v) => set("style", v)} options={[
            { value: "full", label: "Full count with bracha" },
            { value: "count", label: "Count only" },
            { value: "simple", label: "Simple reminder" },
          ]} />
        </Field>
        {draft.style !== "simple" ? (
          <>
            <Field label="Nusach" hint={NUSACH_OPTIONS.find((o) => o.value === draft.nusach)?.hint}>
              <select className="sb-select" value={draft.nusach} onChange={(e) => set("nusach", e.target.value as Nusach)}>
                {NUSACH_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            {draft.nusach === "ashkenaz" && (
              <Check checked={draft.baomer} onChange={(v) => set("baomer", v)}>Say “בָּעֹמֶר” instead of “לָעֹמֶר”</Check>
            )}
            {draft.style === "full" && (
              <div className="sb-grid-2">
                <Field label="Hashem's name in the bracha"
                  hint="A speaker can't say the bracha for you, so by default it reads it the way it is said when learning.">
                  <select className="sb-select" value={draft.divine_name}
                    onChange={(e) => set("divine_name", e.target.value as OmerConfig["divine_name"])}>
                    <option value="hashem">“הַשֵּׁם אֱלֹקֵינוּ”</option>
                    <option value="full">As written in the siddur</option>
                  </select>
                </Field>
                <Field label="Sefirah of the night" hint="e.g. “חֶסֶד שֶׁבִּגְבוּרָה”, after Harachaman.">
                  <select className="sb-select" value={draft.sefirah === null ? "" : String(draft.sefirah)}
                    onChange={(e) => set("sefirah", e.target.value === "" ? null : e.target.value === "true")}>
                    <option value="">As the nusach does ({sefirahDefault ? "say it" : "leave it out"})</option>
                    <option value="true">Say it</option>
                    <option value="false">Leave it out</option>
                  </select>
                </Field>
              </div>
            )}
          </>
        ) : (
          <div className="sb-stack">
            <Field label="Language">
              <Segmented value={draft.simple_language} onChange={(v) => set("simple_language", v)} options={[
                { value: "en", label: "English" }, { value: "he", label: "Hebrew" },
              ]} />
            </Field>
            <Check checked={draft.last_night} onChange={(v) => set("last_night", v)}>Also say what last night's count was</Check>
          </div>
        )}
        {selected && (
          <div className="sb-stack" style={{ gap: 4 }}>
            <small className="sb-hint">Night {selected.night} ({dateShort(selected.evening + "T12:00")} evening) will say:</small>
            <div className="sb-card sb-card-pad" dir={wantLang === "he" ? "rtl" : "ltr"} lang={wantLang}
              style={{ fontSize: 17, lineHeight: 1.7 }}>
              {selected.text}
            </div>
          </div>
        )}
      </div>

      <div className="sb-card sb-card-pad sb-stack">
        <h3 className="sb-section-title">When and where</h3>
        <div className="sb-grid-2">
          <Field label="Time" hint="A zman plus an offset, e.g. tzeit+5m or sunset+44m, or a clock time like 9pm.">
            <ExprInput value={draft.time} onChange={(v) => set("time", v)} previewType="shabbot/omer/preview" quick={OMER_QUICK} />
          </Field>
          <Field label="On Shabbat and Yom Tov nights">
            <select className="sb-select" value={draft.shabbat_yomtov}
              onChange={(e) => set("shabbat_yomtov", e.target.value as OmerConfig["shabbat_yomtov"])}>
              <option value="announce">Announce as usual</option>
              <option value="skip">Don't announce</option>
            </select>
          </Field>
        </div>
        <Field label="Speakers" hint="Media players, speakers or speaker groups. All of them play the announcement together.">
          <EntityMultiPicker value={draft.players} onChange={(v) => set("players", v)} domains={["media_player"]} />
        </Field>
        <VoicesEditor voices={draft.voices} lang={wantLang} onChange={(v) => set("voices", v)} />
        <div className="sb-grid-2">
          <Field label="Volume (%)" hint="Set on the speakers before speaking. Blank = leave as is.">
            <input className="sb-input" type="number" min={0} max={100} value={draft.volume ?? ""}
              onChange={(e) => set("volume", e.target.value === "" ? null : Number(e.target.value))} />
          </Field>
          {draft.voices.length > 1 && (
            <Field label="Pause between voices (seconds)" hint="Long enough for the first voice to finish.">
              <input className="sb-input" type="number" min={0} max={120} value={draft.pause_s}
                onChange={(e) => set("pause_s", Number(e.target.value))} />
            </Field>
          )}
        </div>
        <div className="sb-row">
          <button className="sb-btn" onClick={test} disabled={!draft.players.length || !draft.voices.some((v) => v.engine_id)}>
            Play night {selected?.night ?? "…"} now
          </button>
          {testNote && <span className="sb-hint">{testNote}</span>}
        </div>
      </div>

      <SaveBar dirty={dirty} saving={saving} error={error} onSave={save} onReset={reset} />

      <div className="sb-card sb-stack" style={{ gap: 0 }}>
        <div className="sb-card-pad" style={{ paddingBottom: 0 }}>
          <h3 className="sb-section-title">The 49 nights{nights[0] ? ` of ${nights[0].evening.slice(0, 4)}` : ""}</h3>
          <p className="sb-hint">Click a night to see what will be said. Change any single night here.</p>
        </div>
        {season.isError && <p className="sb-error sb-card-pad">{errorMessage(season.error)}</p>}
        <div className="sb-scroll-x">
          <table className="sb-table">
            <thead>
              <tr><th>Night</th><th>Evening</th><th>Time</th><th></th><th>Announce</th></tr>
            </thead>
            <tbody>
              {nights.map((n) => (
                <tr key={n.evening} onClick={() => setShown(n.night)}
                  style={{ cursor: "pointer", background: n.night === selected?.night ? "var(--accent-soft, rgba(37,99,235,.08))" : undefined }}>
                  <td>{n.night}{n.night === tonight?.night ? " · tonight" : ""}</td>
                  <td>{dateShort(n.evening + "T12:00")}</td>
                  <td>{n.error ? <span className="sb-error">{n.error}</span> : time(n.time)}</td>
                  <td>
                    {n.shabbat && <span className="sb-badge sb-badge-candle">Shabbat</span>}{" "}
                    {n.holiday && <span className="sb-badge sb-badge-candle">{n.holiday}</span>}
                  </td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <select className="sb-select" value={n.choice ?? ""} onChange={(e) => setNight(n.evening, e.target.value)}>
                      <option value="">Default ({defaultFor(n, draft) ? "announce" : "skip"})</option>
                      <option value="announce">Announce</option>
                      <option value="skip">Skip</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const defaultFor = (n: OmerNight, cfg: OmerConfig) => !((n.shabbat || n.holiday) && cfg.shabbat_yomtov === "skip");

/** One or more TTS engines/voices; with two or more the announcement is repeated in each voice. */
function VoicesEditor({ voices, lang, onChange }: { voices: OmerVoice[]; lang: "he" | "en"; onChange: (v: OmerVoice[]) => void }) {
  const engines = useEngines();
  const matches = lang === "he" ? isHebrew : isEnglish;
  const usable = (engines.data ?? []).filter((p) => (p.supported_languages ?? []).some(matches));
  const list = voices.length ? voices : [{ engine_id: "", language: null, voice: null }];
  const update = (i: number, v: OmerVoice) => onChange(list.map((x, j) => (j === i ? v : x)));

  if (engines.isLoading) return <Loading />;
  return (
    <div className="sb-stack">
      {usable.length === 0 && <NoEngineHint lang={lang} />}
      {list.map((v, i) => (
        <VoiceRow key={i} index={i} value={v} engines={usable} matches={matches} onChange={(x) => update(i, x)}
          onRemove={list.length > 1 ? () => onChange(list.filter((_, j) => j !== i)) : undefined} />
      ))}
      {usable.length > 0 && list.length < 4 && (
        <div>
          <button className="sb-btn sb-btn-sm" onClick={() => onChange([...list, { engine_id: "", language: null, voice: null }])}>
            Repeat in another voice
          </button>
        </div>
      )}
    </div>
  );
}

function VoiceRow({ index, value, engines, matches, onChange, onRemove }: {
  index: number; value: OmerVoice; engines: Provider[]; matches: (l: string) => boolean;
  onChange: (v: OmerVoice) => void; onRemove?: () => void;
}) {
  const names = useHassSelector(
    (h) => Object.fromEntries(engines.map((p) => [p.engine_id, (h.states[p.engine_id]?.attributes.friendly_name as string) || p.name || p.engine_id])),
    shallowEqual,
  );
  const engine = engines.find((p) => p.engine_id === value.engine_id);
  const langs = (engine?.supported_languages ?? []).filter(matches);
  const voices = useVoices(value.engine_id, value.language);
  // Pick the engine's language automatically when there is only one sensible choice.
  useEffect(() => {
    if (engine && (!value.language || !langs.includes(value.language)) && langs.length) onChange({ ...value, language: langs[0], voice: null });
  }, [engine?.engine_id, langs.join()]);

  return (
    <div className="sb-grid-2">
      <Field label={index === 0 ? "Text-to-speech engine" : `Then repeat with`}>
        <select className={`sb-select ${value.engine_id && !engine ? "sb-invalid" : ""}`} value={value.engine_id}
          onChange={(e) => onChange({ engine_id: e.target.value, language: null, voice: null })}>
          <option value="">Choose an engine…</option>
          {value.engine_id && !engine && <option value={value.engine_id}>{value.engine_id} (not found)</option>}
          {engines.map((p) => <option key={p.engine_id} value={p.engine_id}>{names[p.engine_id]}</option>)}
        </select>
      </Field>
      {engine && (
        <div className="sb-row" style={{ alignItems: "flex-end" }}>
          {langs.length > 1 && (
            <Field label="Language">
              <select className="sb-select" value={value.language ?? ""} onChange={(e) => onChange({ ...value, language: e.target.value, voice: null })}>
                {langs.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </Field>
          )}
          {(voices.data?.length ?? 0) > 0 && (
            <Field label="Voice">
              <select className="sb-select" value={value.voice ?? ""} onChange={(e) => onChange({ ...value, voice: e.target.value || null })}>
                <option value="">Engine default</option>
                {voices.data!.map((v) => <option key={v.voice_id} value={v.voice_id}>{v.name}</option>)}
              </select>
            </Field>
          )}
          {onRemove && <button className="sb-btn sb-btn-sm" onClick={onRemove}>Remove</button>}
        </div>
      )}
    </div>
  );
}

function NoEngineHint({ lang }: { lang: "he" | "en" }) {
  if (lang === "en") {
    return <div className="sb-banner">No text-to-speech engine with English was found. Add one in Settings → Voice assistants.</div>;
  }
  return (
    <div className="sb-card sb-card-pad sb-stack" style={{ borderColor: "var(--warn)" }}>
      <strong>No text-to-speech engine that speaks Hebrew was found.</strong>
      <span className="sb-hint">Add one of these in Home Assistant, then come back and choose it here:</span>
      <ul style={{ margin: 0, paddingInlineStart: 20, lineHeight: 1.6 }}>
        <li>
          <b>Home Assistant Cloud</b>: if you subscribe to Nabu Casa, its speech already includes Hebrew neural voices
          (Avri, Hila). <a href="/config/cloud" target="_top">Open Cloud settings</a>
        </li>
        <li>
          <b>Microsoft Azure Speech</b>: the best Hebrew voices (Avri, Hila). Azure's free tier covers a nightly Omer
          announcement easily; it needs a free Azure account and key.{" "}
          <a href="https://www.home-assistant.io/integrations/microsoft/" target="_blank" rel="noreferrer">How to set it up</a>
        </li>
        <li>
          <b>Google Translate text-to-speech</b>: free, no account, set up in a minute. The voice is plainer and less
          accurate with nikud.{" "}
          <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=google_translate" target="_blank" rel="noreferrer">Add it</a>
        </li>
      </ul>
      <span className="sb-hint">Or switch to the simple reminder in English, which works with any engine.</span>
    </div>
  );
}
