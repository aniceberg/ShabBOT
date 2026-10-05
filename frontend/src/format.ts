// Date/time formatting in Home Assistant's time zone (the house's, not the browser's).

let tz: string | undefined;
export const setTimeZone = (zone: string) => {
  tz = zone;
};

const fmt = (opts: Intl.DateTimeFormatOptions) => (iso: string | Date | null | undefined) =>
  iso ? new Intl.DateTimeFormat(undefined, { timeZone: tz, ...opts }).format(new Date(iso)) : "—";

export const time = fmt({ hour: "numeric", minute: "2-digit" });
export const dayTime = fmt({ weekday: "short", hour: "numeric", minute: "2-digit" });
export const dateLong = fmt({ weekday: "long", month: "long", day: "numeric", year: "numeric" });
export const dateShort = fmt({ weekday: "short", month: "short", day: "numeric" });
export const dateTime = fmt({ month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export const isoDate = (d: Date) => {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

export const addDays = (d: Date, n: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);

export const PART_LABEL: Record<string, string> = { night: "Night meal", day: "Day meal", block: "Baseline" };
export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const HOLIDAY_LABEL: Record<string, string> = {
  rosh_hashana: "Rosh Hashana",
  yom_kippur: "Yom Kippur",
  sukkot: "Sukkot",
  shmini_atzeret: "Shmini Atzeret",
  simchat_torah: "Simchat Torah",
  pesach: "Pesach",
  shavuot: "Shavuot",
};
export const DAY_TYPE_LABEL: Record<string, string> = {
  shabbat: "Shabbat (incl. Yom Tov on Shabbat)",
  yomtov: "Yom Tov (incl. on Shabbat)",
  shabbat_only: "Plain Shabbat",
  yomtov_only: "Yom Tov on a weekday",
};
export const ANCHOR_LABEL: Record<string, string> = {
  alot: "Dawn (alot)",
  sunrise: "Sunrise",
  chatzot: "Midday (chatzot)",
  mincha_gedola: "Mincha gedola",
  plag: "Plag hamincha",
  candle_lighting: "Candle lighting",
  sunset: "Sunset",
  tzeit: "Nightfall (tzeit)",
  havdalah: "Havdalah (end of Shabbat/Yom Tov)",
  midnight: "Midnight",
  slot_start: "Start of this meal period",
  slot_end: "End of this meal period",
  block_start: "Candle lighting (start of Shabbat/Yom Tov)",
  block_end: "Havdalah (end of Shabbat/Yom Tov)",
};

/** Short names for the "Insert time" chips. */
export const ANCHOR_CHIP: Record<string, string> = {
  sunset: "Sunset",
  candle_lighting: "Candle lighting",
  tzeit: "Nightfall",
  havdalah: "Havdalah",
  midnight: "Midnight",
  sunrise: "Sunrise",
  chatzot: "Midday",
};

const EXPR_ALIASES: Record<string, string> = {
  candles: "candle_lighting", candlelighting: "candle_lighting", nightfall: "tzeit",
  start: "slot_start", end: "slot_end", "12am": "midnight",
};

/** Plain-language reading of a time expression, e.g. "sunset+18m" → "Sunset + 18m". Null for clock times etc. */
export function describeExpr(expr: string): string | null {
  const m = expr.trim().toLowerCase().match(/^([a-z_]+)\s*(.*)$/);
  if (!m) return null;
  const label = ANCHOR_LABEL[EXPR_ALIASES[m[1]] ?? m[1]];
  if (!label) return null;
  const offset = m[2].replace(/\s+/g, "").replace(/([+-])/g, " $1 ").trim();
  return offset ? `${label} ${offset}` : label;
}
