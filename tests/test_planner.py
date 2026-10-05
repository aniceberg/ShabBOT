"""Time expressions, rule resolution and the desired-state timeline."""

from datetime import date, datetime, timedelta

import pytest

from custom_components.shabbot.core import astro, jcal, planner, timeexpr

BROOKLYN = astro.Location(40.6501, -73.94958, "America/New_York", 18)
TZ = BROOKLYN.tzinfo
MINHAG = jcal.Minhag()


def _slot(day: date, part: str) -> jcal.Slot:
    (block,) = jcal.blocks_between(day, day, BROOKLYN, MINHAG)
    return next(s for s in block.slots if s.key == f"{day.isoformat()}/{part}")


def _eval(expr: str, slot: jcal.Slot) -> datetime:
    return timeexpr.evaluate(expr, slot.anchors, slot.base_date, slot.part is jcal.Part.NIGHT, TZ)


# ---------------------------------------------------------------- time expressions

FRI_NIGHT = date(2026, 10, 10)  # Shabbat Bereshit


def test_offsets_and_clock_times() -> None:
    slot = _slot(FRI_NIGHT, "night")
    sunset = slot.anchors["sunset"]
    assert sunset.date() == date(2026, 10, 9)
    assert _eval("sunset+18m", slot) == sunset + timedelta(minutes=18)
    assert _eval("sunset + 2h", slot) == sunset + timedelta(hours=2)
    assert _eval("Sunset+1h30m-5min", slot) == sunset + timedelta(minutes=85)
    assert _eval("11:45pm", slot) == datetime(2026, 10, 9, 23, 45, tzinfo=TZ)
    assert _eval("23:45", slot) == datetime(2026, 10, 9, 23, 45, tzinfo=TZ)
    # Night slots: morning clock times roll to the next day.
    assert _eval("1:30am", slot) == datetime(2026, 10, 10, 1, 30, tzinfo=TZ)
    assert _eval("midnight", slot) == datetime(2026, 10, 10, 0, 0, tzinfo=TZ)
    assert _eval("candles", slot) == slot.anchors["candle_lighting"]
    assert _eval("max(sunset+18m, 7pm)", slot) == datetime(2026, 10, 9, 19, 0, tzinfo=TZ)
    assert _eval("min(sunset+18m, 7pm)", slot) == sunset + timedelta(minutes=18)


def test_day_slot_clock_times() -> None:
    slot = _slot(FRI_NIGHT, "day")
    assert _eval("11:30am", slot) == datetime(2026, 10, 10, 11, 30, tzinfo=TZ)
    assert _eval("havdalah", slot) == slot.anchors["havdalah"]


@pytest.mark.parametrize("bad", ["sunrize", "sunset+", "sunset 18m", "25:00", "max(sunset", "sunset+18x", ""])
def test_invalid_expressions(bad: str) -> None:
    with pytest.raises(timeexpr.ExprError):
        timeexpr.validate(bad)


# ---------------------------------------------------------------- resolution


def _action(aid: str, entity: str, start: str, end: str, state: str = "on") -> dict:
    return {"id": aid, "entity_id": entity, "state": state, "start": start, "end": end}


CONFIG = {
    "routines": {
        "std_night": {"id": "std_night", "name": "Standard Friday night", "part": "night", "actions": [
            _action("a1", "light.chandelier", "sunset+18m", "11:45pm"),
            _action("a2", "switch.hotplate", "sunset", "sunset+2h"),
            _action("a3", "light.living_room", "sunset", "midnight"),
        ]},
        "hosting": {"id": "hosting", "name": "Friday night hosting", "part": "night", "actions": [
            _action("h1", "light.chandelier", "sunset+18m", "1:00am"),
        ]},
        "away": {"id": "away", "name": "Away", "part": "night", "actions": []},
        "yt_night": {"id": "yt_night", "name": "Yom Tov home", "part": "night", "actions": []},
        "lunch": {"id": "lunch", "name": "Lunch", "part": "day", "actions": [
            _action("l1", "switch.hotplate", "7am", "2pm"),
        ]},
        "baseline": {"id": "baseline", "name": "Baseline", "part": "block", "actions": [
            _action("b1", "light.bedroom", "block_start", "block_end", state="off"),
            _action("b2", "light.chandelier", "block_start", "block_end", state="off"),
        ]},
    },
    "rules": [
        {"id": "r1", "name": "Shabbat night", "part": "night", "match": {"day_type": "shabbat"}, "routine_id": "std_night"},
        {"id": "r2", "name": "YT night", "part": "night", "match": {"day_type": "yomtov"}, "routine_id": "yt_night"},
        {"id": "r3", "name": "Pesach 2nd night", "part": "night",
         "match": {"holiday_group": "pesach", "day_in_block": 2}, "routine_id": "hosting"},
        {"id": "r4", "name": "Lunch", "part": "day", "match": {}, "routine_id": "lunch"},
        {"id": "r5", "name": "Baseline", "part": "block", "match": {}, "routine_id": "baseline"},
    ],
    "modes": [],
    "assignments": {},
}


def _target(key: str) -> planner.Target:
    day = date.fromisoformat(key.split("/")[0])
    (block,) = jcal.blocks_between(day, day, BROOKLYN, MINHAG)
    return next(t for t in planner.targets_for_block(block) if t.key == key)


def test_rule_specificity() -> None:
    # Pesach 2027: Thu (YT1), Fri (YT2), Sat (Shabbat). Night 2 has the specific Pesach rule.
    assert planner.resolve(_target("2027-04-22/night"), CONFIG).routine_id == "yt_night"
    assert planner.resolve(_target("2027-04-23/night"), CONFIG).routine_id == "hosting"
    assert planner.resolve(_target("2027-04-24/night"), CONFIG).routine_id == "std_night"  # first matching rule wins ties
    assert planner.resolve(_target("2027-04-22/block"), CONFIG).routine_id == "baseline"


def test_assignment_overrides_and_skip() -> None:
    cfg = {**CONFIG, "assignments": {
        "2026-10-10/night": {"routine_id": "hosting"},
        "2026-10-10/day": {"skip": True},
    }}
    res = planner.resolve(_target("2026-10-10/night"), cfg)
    assert (res.routine_id, res.source, res.default_routine_id) == ("hosting", "assignment", "std_night")
    res = planner.resolve(_target("2026-10-10/day"), cfg)
    assert (res.routine_id, res.source, res.default_routine_id) == (None, "skipped", "lunch")
    # The general rule still applies the following week.
    assert planner.resolve(_target("2026-10-17/day"), cfg).routine_id == "lunch"


def test_modes_open_ended_and_bounded() -> None:
    cfg = {**CONFIG, "modes": [
        {"id": "m1", "name": "Summer", "enabled": True, "start": "2026-10-15", "end": None,
         "night": "away", "day": "none", "block": None},
    ]}
    assert planner.resolve(_target("2026-10-10/night"), cfg).routine_id == "std_night"
    res = planner.resolve(_target("2026-10-17/night"), cfg)
    assert (res.routine_id, res.source, res.source_name) == ("away", "mode", "Summer")
    assert planner.resolve(_target("2026-10-17/day"), cfg).routine_id is None
    assert planner.resolve(_target("2026-10-17/block"), cfg).routine_id == "baseline"  # None falls through
    cfg["modes"][0]["end"] = "2026-10-20"
    assert planner.resolve(_target("2026-10-24/night"), cfg).routine_id == "std_night"


# ---------------------------------------------------------------- timeline


def test_timeline_layers_meal_over_baseline() -> None:
    _, instances = planner.plan_range(date(2026, 10, 10), date(2026, 10, 10), BROOKLYN, MINHAG, CONFIG)
    tl = planner.Timeline(instances)
    night = _slot(FRI_NIGHT, "night")
    sunset = night.anchors["sunset"]
    # Before sunset+18m the baseline keeps the chandelier off; then the meal routine turns it on.
    assert tl.desired_at("light.chandelier", sunset + timedelta(minutes=5)).state == "off"
    assert tl.desired_at("light.chandelier", sunset + timedelta(minutes=30)).state == "on"
    assert tl.desired_at("light.chandelier", datetime(2026, 10, 9, 23, 50, tzinfo=TZ)).state == "off"
    # Hotplate: on for 2h, then unmanaged with a one-shot "off".
    assert tl.desired_at("switch.hotplate", sunset + timedelta(hours=1)).state == "on"
    assert tl.desired_at("switch.hotplate", sunset + timedelta(hours=3)) is None
    ending = tl.ending_at("switch.hotplate", sunset + timedelta(hours=2))
    assert ending is not None and ending.end_state == "off"
    nb = tl.next_boundary(sunset)
    assert nb == sunset + timedelta(minutes=18)
    assert "light.chandelier" in tl.entities_with_boundary(nb)


def test_instance_span_and_errors() -> None:
    cfg = {**CONFIG, "routines": {**CONFIG["routines"], "bad": {"id": "bad", "name": "Bad", "part": "night",
           "actions": [_action("x", "light.x", "sunset", "sunset-1h"), _action("y", "light.y", "nope", "sunset")]}},
           "assignments": {"2026-10-10/night": {"routine_id": "bad"}}}
    _, instances = planner.plan_range(date(2026, 10, 10), date(2026, 10, 10), BROOKLYN, MINHAG, cfg)
    inst = next(i for i in instances if i.target.key == "2026-10-10/night")
    assert inst.actions[0].error == "End is not after start"
    assert "Unknown time" in inst.actions[1].error
    std = next(i for i in instances if i.target.key == "2026-10-10/day")
    assert std.start == datetime(2026, 10, 10, 7, 0, tzinfo=TZ)
    assert std.end == datetime(2026, 10, 10, 14, 0, tzinfo=TZ)
