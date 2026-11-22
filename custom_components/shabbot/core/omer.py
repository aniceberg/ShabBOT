"""Sefirat Haomer: which night of the Omer it is, and the words to say.

The Omer is counted at night. Night 1 is the evening that begins 16 Nissan (the second night of Pesach),
night 49 the evening that begins 5 Sivan (Erev Shavuot). Everything here is keyed by the *civil date of the
evening*: `omer_night(date(2026, 4, 2)) == 1`.

Nusach differences in the count itself:
  * Edot Hamizrach (Sephardi): "לָעֹמֶר" comes right after the days, before the weeks
    ("הַיּוֹם שְׁמוֹנָה יָמִים לָעֹמֶר שֶׁהֵם שָׁבוּעַ אֶחָד וְיוֹם אֶחָד").
  * Ashkenaz: "לָעֹמֶר" at the end, after the weeks. The Rema has "בָּעֹמֶר"; most printed siddurim have
    "לָעֹמֶר". Both are offered.
  * Sefard (Chassidic) and Chabad: "לָעֹמֶר" at the end, like Ashkenaz. They differ from Ashkenaz in what is
    said around the count (e.g. the sefirah of the night), not in the count.
The numbers themselves are the same in all of them.
"""

from __future__ import annotations

from datetime import date, timedelta

from pyluach.dates import GregorianDate

NISSAN, IYAR, SIVAN = 1, 2, 3
NUSACHS = ("edot_hamizrach", "ashkenaz", "sefard")
STYLES = ("full", "count", "simple")

HAYOM = "הַיּוֹם"
LAOMER = "לָעֹמֶר"
BAOMER = "בָּעֹמֶר"
SHEHEM = "שֶׁהֵם"

# Cardinal numbers as said with יָמִים / שָׁבוּעוֹת (masculine nouns take the "ה" forms from 3 up).
_UNITS = {3: "שְׁלֹשָׁה", 4: "אַרְבָּעָה", 5: "חֲמִשָּׁה", 6: "שִׁשָּׁה", 7: "שִׁבְעָה", 8: "שְׁמוֹנָה", 9: "תִּשְׁעָה"}
_TEENS = {11: "אַחַד עָשָׂר", 12: "שְׁנֵים עָשָׂר"} | {10 + u: f"{w} עָשָׂר" for u, w in _UNITS.items()}
_TENS = {20: "עֶשְׂרִים", 30: "שְׁלֹשִׁים", 40: "אַרְבָּעִים"}
_TENS_AND = {20: "וְעֶשְׂרִים", 30: "וּשְׁלֹשִׁים", 40: "וְאַרְבָּעִים"}
_UNITS_COMPOUND = {1: "אֶחָד", 2: "שְׁנַיִם", **_UNITS}
# "…and N days" after the weeks.
_REMAINDER = {1: "וְיוֹם אֶחָד", 2: "וּשְׁנֵי יָמִים", 3: "וּשְׁלֹשָׁה יָמִים", 4: "וְאַרְבָּעָה יָמִים",
              5: "וַחֲמִשָּׁה יָמִים", 6: "וְשִׁשָּׁה יָמִים"}
_WEEKS = {1: "שָׁבוּעַ אֶחָד", 2: "שְׁנֵי שָׁבוּעוֹת", **{w: f"{_UNITS[w]} שָׁבוּעוֹת" for w in range(3, 8)}}

# Sefirot of the seven weeks/days, and the same with the "שֶׁבְּ" prefix.
_MIDDOT = ("חֶסֶד", "גְּבוּרָה", "תִּפְאֶרֶת", "נֶצַח", "הוֹד", "יְסוֹד", "מַלְכוּת")
_SHEB = ("שֶׁבְּחֶסֶד", "שֶׁבִּגְבוּרָה", "שֶׁבְּתִפְאֶרֶת", "שֶׁבְּנֶצַח", "שֶׁבְּהוֹד", "שֶׁבִּיסוֹד", "שֶׁבְּמַלְכוּת")

BRACHA_HASHEM = "בָּרוּךְ אַתָּה הַשֵּׁם אֱלֹקֵינוּ מֶלֶךְ הָעוֹלָם"
BRACHA_FULL = "בָּרוּךְ אַתָּה אֲדֹנָי אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם"
BRACHA_END = "אֲשֶׁר קִדְּשָׁנוּ בְּמִצְוֹתָיו וְצִוָּנוּ עַל סְפִירַת הָעֹמֶר"
HARACHAMAN = ("הָרַחֲמָן הוּא יַחֲזִיר לָנוּ עֲבוֹדַת בֵּית הַמִּקְדָּשׁ לִמְקוֹמָהּ "
              "בִּמְהֵרָה בְיָמֵינוּ אָמֵן סֶלָה")


def _check(n: int) -> None:
    if not 1 <= n <= 49:
        raise ValueError(f"Omer night must be 1–49, got {n}")


def omer_night(evening: date) -> int | None:
    """The Omer count said on the evening of this civil date, or None outside the Omer."""
    h = (GregorianDate(evening.year, evening.month, evening.day) + 1).to_heb()
    if h.month == NISSAN and h.day >= 16:
        return h.day - 15
    if h.month == IYAR:
        return h.day + 15
    if h.month == SIVAN and h.day <= 5:
        return h.day + 44
    return None


def omer_season(around: date) -> list[date]:
    """The 49 evenings of the Omer season that hasn't finished by `around` (this year's, or next year's)."""
    d = around
    for _ in range(400):
        n = omer_night(d)
        if n is not None:
            first = d - timedelta(days=n - 1)
            return [first + timedelta(days=i) for i in range(49)]
        d += timedelta(days=1)
    raise RuntimeError("No Omer found within a year")  # pragma: no cover - unreachable


def days_phrase(n: int) -> str:
    """'שְׁמוֹנָה יָמִים', 'אַחַד עָשָׂר יוֹם', 'אֶחָד וְעֶשְׂרִים יוֹם'…"""
    _check(n)
    if n == 1:
        return "יוֹם אֶחָד"
    if n == 2:
        return "שְׁנֵי יָמִים"
    if n <= 9:
        return f"{_UNITS[n]} יָמִים"
    if n == 10:
        return "עֲשָׂרָה יָמִים"
    if n < 20:
        return f"{_TEENS[n]} יוֹם"
    tens, units = n - n % 10, n % 10
    if units == 0:
        return f"{_TENS[tens]} יוֹם"
    return f"{_UNITS_COMPOUND[units]} {_TENS_AND[tens]} יוֹם"


def weeks_phrase(n: int) -> str | None:
    """'שָׁבוּעַ אֶחָד וְיוֹם אֶחָד' for night 8; None before the first week is complete."""
    _check(n)
    weeks, rest = divmod(n, 7)
    if weeks == 0:
        return None
    return f"{_WEEKS[weeks]} {_REMAINDER[rest]}" if rest else _WEEKS[weeks]


def count_line(n: int, nusach: str = "edot_hamizrach", baomer: bool = False) -> str:
    """The count itself, as said in this nusach."""
    if nusach not in NUSACHS:
        raise ValueError(f"Unknown nusach {nusach!r}")
    days, weeks = days_phrase(n), weeks_phrase(n)
    if nusach == "edot_hamizrach":
        return f"{HAYOM} {days} {LAOMER}" + (f" {SHEHEM} {weeks}" if weeks else "")
    omer = BAOMER if nusach == "ashkenaz" and baomer else LAOMER
    return f"{HAYOM} {days}" + (f" {SHEHEM} {weeks}" if weeks else "") + f" {omer}"


def sefirah(n: int) -> str:
    """The sefirah of the night: 'חֶסֶד שֶׁבְּחֶסֶד' (night 1) … 'מַלְכוּת שֶׁבְּמַלְכוּת' (night 49)."""
    _check(n)
    week, day = divmod(n - 1, 7)
    return f"{_MIDDOT[day]} {_SHEB[week]}"


def bracha(full_name: bool = False) -> str:
    return f"{BRACHA_FULL if full_name else BRACHA_HASHEM} {BRACHA_END}"


def full_text(n: int, nusach: str = "edot_hamizrach", *, full_name: bool = False, with_sefirah: bool | None = None,
              baomer: bool = False) -> str:
    """Bracha, the count, Harachaman and (by default, except in Ashkenaz) the sefirah of the night."""
    if with_sefirah is None:
        with_sefirah = nusach != "ashkenaz"
    parts = [bracha(full_name), count_line(n, nusach, baomer), HARACHAMAN]
    if with_sefirah:
        parts.append(sefirah(n))
    return ". ".join(parts) + "."


_ORD_SMALL = ("zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
              "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth",
              "eighteenth", "nineteenth")
_TENS_WORD = {20: "twenty", 30: "thirty", 40: "forty"}
_TENS_ORD = {20: "twentieth", 30: "thirtieth", 40: "fortieth"}


def english_ordinal(n: int) -> str:
    """1 → 'first', 22 → 'twenty-second', 40 → 'fortieth'."""
    _check(n)
    if n < 20:
        return _ORD_SMALL[n]
    tens, units = n - n % 10, n % 10
    return _TENS_ORD[tens] if units == 0 else f"{_TENS_WORD[tens]}-{_ORD_SMALL[units]}"


def simple_text(n: int, language: str = "en", last_night: bool = False) -> str:
    """'Tonight is the eighth night of the Omer.' (+ 'Last night was the seventh…')."""
    _check(n)
    if language == "he":
        text = f"הַלַּיְלָה סוֹפְרִים {days_phrase(n)} {LAOMER}."
        if last_night and n > 1:
            text += f" אֶמֶשׁ סָפַרְנוּ {days_phrase(n - 1)} {LAOMER}."
        return text
    text = f"Tonight is the {english_ordinal(n)} night of the Omer."
    if last_night and n > 1:
        text += f" Last night was the {english_ordinal(n - 1)} night of the Omer."
    return text


def announcement(n: int, cfg: dict) -> str:
    """The text to speak for night `n` with an Omer config (see const.DEFAULT_OMER)."""
    style = cfg.get("style", "full")
    nusach = cfg.get("nusach", "edot_hamizrach")
    baomer = bool(cfg.get("baomer"))
    if style == "simple":
        return simple_text(n, cfg.get("simple_language", "en"), bool(cfg.get("last_night")))
    if style == "count":
        return count_line(n, nusach, baomer)
    return full_text(n, nusach, full_name=cfg.get("divine_name") == "full", with_sefirah=cfg.get("sefirah"),
                     baomer=baomer)


__all__ = [
    "NUSACHS", "STYLES", "announcement", "bracha", "count_line", "days_phrase", "english_ordinal", "full_text",
    "omer_night", "omer_season", "sefirah", "simple_text", "weeks_phrase",
]
