"""Check blocks, candle lighting and havdalah against hebcal.com reference data."""

from datetime import date, datetime, timedelta
import json
from pathlib import Path

import pytest

from custom_components.shabbot.core import astro, jcal

FIXTURES = Path(__file__).parent / "fixtures"
BROOKLYN = astro.Location(40.6501, -73.94958, "America/New_York", 18)
JERUSALEM = astro.Location(31.76904, 35.21633, "Asia/Jerusalem", 786)


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())["items"]


def _expected(items: list[dict]) -> tuple[list[datetime], list[datetime], set[date]]:
    candles = [datetime.fromisoformat(i["date"]) for i in items if i["category"] == "candles"]
    havdalah = [datetime.fromisoformat(i["date"]) for i in items if i["category"] == "havdalah"]
    yomtov = {date.fromisoformat(i["date"]) for i in items if i.get("yomtov")}
    return candles, havdalah, yomtov


CASES = [
    ("hebcal_brooklyn_2026.json", BROOKLYN, jcal.Minhag(), 2026),
    ("hebcal_brooklyn_2027.json", BROOKLYN, jcal.Minhag(), 2027),
    ("hebcal_jerusalem_2027.json", JERUSALEM, jcal.Minhag(candle_lighting_min=40, israel=True), 2027),
]


@pytest.mark.parametrize(("fixture", "loc", "minhag", "year"), CASES)
def test_yom_tov_days_match_hebcal(fixture, loc, minhag, year) -> None:
    _, _, expected = _expected(_load(fixture))
    d, ours = date(year, 1, 1), set()
    while d.year == year:
        if jcal.yom_tov(d, minhag.israel):
            ours.add(d)
        d += timedelta(days=1)
    assert ours == expected


@pytest.mark.parametrize(("fixture", "loc", "minhag", "year"), CASES)
def test_block_boundaries_match_hebcal(fixture, loc, minhag, year) -> None:
    candles, havdalah, _ = _expected(_load(fixture))
    blocks = jcal.blocks_between(date(year, 1, 2), date(year, 12, 29), loc, minhag)
    starts = {b.start for b in blocks}
    ends = {b.end for b in blocks}
    in_range = lambda t: date(year, 1, 2) <= t.date() <= date(year, 12, 28)  # noqa: E731
    # Every block start is a hebcal candle lighting (within a minute), and every havdalah is a block end.
    for t in filter(in_range, starts):
        assert any(abs((t - c).total_seconds()) <= 60 for c in candles), t
    for h in filter(in_range, havdalah):
        assert any(abs((h - e).total_seconds()) <= 60 for e in ends), h
    # Candle lightings inside blocks are the night starts of later slots.
    slot_starts = [s.start for b in blocks for s in b.slots if s.part is jcal.Part.NIGHT]
    for c in filter(in_range, candles):
        assert any(abs((c - s).total_seconds()) <= 60 for s in slot_starts), c


def test_pesach_2027_three_day_block() -> None:
    blocks = jcal.blocks_between(date(2027, 4, 22), date(2027, 4, 22), BROOKLYN, jcal.Minhag())
    assert len(blocks) == 1
    b = blocks[0]
    assert [d.isoformat() for d in b.days] == ["2027-04-22", "2027-04-23", "2027-04-24"]
    assert b.title == "Shabbat + Pesach I + Pesach II"
    nights = [s for s in b.slots if s.part is jcal.Part.NIGHT]
    # Night 2 (YT after YT) starts after tzeit; night 3 (into Shabbat) at candle lighting before sunset.
    assert nights[1].start > nights[1].anchors["sunset"]
    assert nights[2].start < nights[2].anchors["sunset"]
    assert [s.day_in_block for s in nights] == [1, 2, 3]


def test_block_at() -> None:
    fri_evening = datetime(2026, 10, 9, 20, 0, tzinfo=BROOKLYN.tzinfo)
    b = jcal.block_at(fri_evening, BROOKLYN, jcal.Minhag())
    assert b is not None and b.id == "2026-10-10"
    assert jcal.block_at(datetime(2026, 10, 7, 12, tzinfo=BROOKLYN.tzinfo), BROOKLYN, jcal.Minhag()) is None


def test_zmanim_against_hebcal() -> None:
    times = json.loads((FIXTURES / "zmanim_brooklyn_2026q4.json").read_text())["times"]
    for key, attr in [("sunrise", "sunrise"), ("sunset", "sunset"), ("tzeit85deg", "tzeit"),
                      ("chatzot", "chatzot"), ("alotHaShachar", "alot"), ("plagHaMincha", "plag")]:
        for ds, v in times[key].items():
            ours = getattr(jcal.Zmanim(date.fromisoformat(ds), BROOKLYN, jcal.Minhag()), attr)
            assert abs((ours - datetime.fromisoformat(v)).total_seconds()) <= 5, (key, ds)
