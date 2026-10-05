"""Time expressions used by routine actions.

Grammar (whitespace-insensitive, case-insensitive):

    expr     := func "(" expr ("," expr)* ")" | term
    func     := "min" | "max"
    term     := (anchor | clock) (("+" | "-") duration)*
    duration := e.g. "18m", "2h", "1h30m", "90min"
    clock    := "23:45", "11:45pm", "7am"

Anchors come from the slot (see jcal.Slot.anchors): sunrise, sunset,
candle_lighting, havdalah, tzeit, chatzot, plag, alot, mincha_gedola,
midnight, slot_start, slot_end, block_start, block_end.

Clock times resolve on the slot's base date; for night slots, clock times
before 12:00 resolve on the following morning (e.g. "1:00am" after the meal).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo
import re

ANCHORS = (
    "alot", "sunrise", "chatzot", "mincha_gedola", "plag", "candle_lighting", "sunset", "tzeit",
    "havdalah", "midnight", "slot_start", "slot_end", "block_start", "block_end",
)
_ALIASES = {"candles": "candle_lighting", "candlelighting": "candle_lighting", "nightfall": "tzeit",
            "start": "slot_start", "end": "slot_end", "12am": "midnight"}

_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<clock>\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2})"
    r"|(?P<dur>(?:\d+\s*(?:hours?|hrs|hr|h|minutes?|mins|min|m)(?![a-z])\s*)+)"
    r"|(?P<name>[a-z_][a-z0-9_]*)"
    r"|(?P<op>[+\-(),])"
    r")",
    re.IGNORECASE,
)
_DUR_PART = re.compile(r"(\d+)\s*(hours?|hrs|hr|h|minutes?|mins|min|m)", re.IGNORECASE)


class ExprError(ValueError):
    """Invalid time expression."""


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ExprError(f"Unexpected text at position {pos}: {text[pos:]!r}")
        kind = m.lastgroup
        assert kind is not None
        tokens.append((kind, m.group(kind).strip().lower()))
        pos = m.end()
    return tokens


def _parse_duration(text: str) -> timedelta:
    total = timedelta()
    for qty, unit in _DUR_PART.findall(text):
        total += timedelta(hours=int(qty)) if unit.lower().startswith("h") else timedelta(minutes=int(qty))
    return total


def _parse_clock(text: str) -> time:
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text.strip().lower())
    if not m:
        raise ExprError(f"Bad clock time {text!r}")
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ampm:
        if not 1 <= hour <= 12:
            raise ExprError(f"Bad clock time {text!r}")
        hour = hour % 12 + (12 if ampm == "pm" else 0)
    if hour > 23 or minute > 59:
        raise ExprError(f"Bad clock time {text!r}")
    return time(hour, minute)


class _Context:
    def __init__(self, anchors: dict[str, datetime], base_date: date, night: bool, tz: tzinfo) -> None:
        self.anchors = anchors
        self.base_date = base_date
        self.night = night
        self.tz = tz

    def clock(self, t: time) -> datetime:
        d = self.base_date
        if self.night and t.hour < 12:
            d += timedelta(days=1)
        return datetime.combine(d, t, tzinfo=self.tz)


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], ctx: _Context | None) -> None:
        self.tokens = tokens
        self.i = 0
        self.ctx = ctx

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ExprError("Unexpected end of expression")
        self.i += 1
        return tok

    def expect(self, value: str) -> None:
        kind, val = self.take()
        if val != value:
            raise ExprError(f"Expected {value!r}, got {val!r}")

    def parse(self) -> datetime | None:
        result = self.expr()
        if self.peek() is not None:
            raise ExprError(f"Unexpected {self.peek()[1]!r}")  # type: ignore[index]
        return result

    def expr(self) -> datetime | None:
        kind, val = self.peek() or ("", "")
        if kind == "name" and val in ("min", "max"):
            self.take()
            self.expect("(")
            values = [self.expr()]
            while (self.peek() or ("", ""))[1] == ",":
                self.take()
                values.append(self.expr())
            self.expect(")")
            if self.ctx is None:
                return None
            present = [v for v in values if v is not None]
            if not present:
                return None
            return min(present) if val == "min" else max(present)
        return self.term()

    def term(self) -> datetime | None:
        kind, val = self.take()
        base: datetime | None
        if kind == "clock":
            t = _parse_clock(val)
            base = self.ctx.clock(t) if self.ctx else None
        elif kind == "name":
            name = _ALIASES.get(val, val)
            if name not in ANCHORS:
                raise ExprError(f"Unknown time {val!r}. Use one of: {', '.join(ANCHORS)}")
            base = self.ctx.anchors.get(name) if self.ctx else None
            if self.ctx and base is None:
                raise ExprError(f"{name!r} is not available here")
        else:
            raise ExprError(f"Expected a time, got {val!r}")
        while (self.peek() or ("", ""))[1] in ("+", "-"):
            _, sign = self.take()
            dkind, dval = self.take()
            if dkind != "dur":
                raise ExprError(f"Expected a duration like 18m or 2h after {sign!r}, got {dval!r}")
            delta = _parse_duration(dval)
            if base is not None:
                base = base + delta if sign == "+" else base - delta
        return base


def validate(text: str) -> None:
    """Raise ExprError if the expression is syntactically invalid."""
    _Parser(_tokenize(text), None).parse()


def evaluate(text: str, anchors: dict[str, datetime], base_date: date, night: bool, tz: tzinfo) -> datetime:
    """Evaluate an expression against a slot's anchors."""
    result = _Parser(_tokenize(text), _Context(anchors, base_date, night, tz)).parse()
    if result is None:
        raise ExprError(f"{text!r} did not resolve to a time")
    return result
