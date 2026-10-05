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
  havdalah: "Havdalah",
  midnight: "Midnight",
  slot_start: "Meal period start",
  slot_end: "Meal period end",
  block_start: "Shabbat/YT start",
  block_end: "Shabbat/YT end",
};
