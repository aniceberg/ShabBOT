"""Sefirat Haomer: the night of the count, the words, and the nightly announcement inside Home Assistant."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.shabbot.const import DOMAIN
from custom_components.shabbot.core import omer
from custom_components.shabbot.manager import ShabbotManager
from custom_components.shabbot.omer import tts_call

FIXTURES = Path(__file__).parent / "fixtures"
TZ = ZoneInfo("America/New_York")

# ---------------------------------------------------------------- which night


@pytest.mark.parametrize(("evening", "night"), [
    (date(2026, 4, 1), None),  # Erev Pesach: no count yet
    (date(2026, 4, 2), 1),  # first Seder night (15 Nissan) → the count for 16 Nissan
    (date(2026, 4, 15), 14),
    (date(2026, 5, 4), 33),  # Lag Ba'omer
    (date(2026, 5, 20), 49),  # Erev Shavuot
    (date(2026, 5, 21), None),  # Shavuot night
    (date(2027, 4, 22), 1),
    (date(2027, 6, 9), 49),
    (date(2026, 11, 21), None),
])
def test_omer_night(evening: date, night: int | None) -> None:
    assert omer.omer_night(evening) == night


def test_season_is_49_consecutive_evenings() -> None:
    season = omer.omer_season(date(2026, 4, 10))
    assert season[0] == date(2026, 4, 2) and season[-1] == date(2026, 5, 20) and len(season) == 49
    assert [omer.omer_night(d) for d in season] == list(range(1, 50))
    # After Shavuot the next season is next year's.
    assert omer.omer_season(date(2026, 5, 21))[0] == date(2027, 4, 22)


# ---------------------------------------------------------------- the words


def test_edot_hamizrach_matches_reference_automation() -> None:
    """Every night word-for-word as in the Edot Hamizrach automation ShabBOT replaces."""
    reference = json.loads((FIXTURES / "omer_edot_hamizrach.json").read_text())
    for n in range(1, 50):
        assert omer.count_line(n, "edot_hamizrach") == reference[str(n)], n


@pytest.mark.parametrize("nusach", ["ashkenaz", "sefard"])
def test_laomer_after_the_weeks(nusach: str) -> None:
    assert omer.count_line(8, nusach) == "הַיּוֹם שְׁמוֹנָה יָמִים שֶׁהֵם שָׁבוּעַ אֶחָד וְיוֹם אֶחָד לָעֹמֶר"
    assert omer.count_line(3, nusach) == "הַיּוֹם שְׁלֹשָׁה יָמִים לָעֹמֶר"


def test_ashkenaz_baomer() -> None:
    assert omer.count_line(49, "ashkenaz", baomer=True) == "הַיּוֹם תִּשְׁעָה וְאַרְבָּעִים יוֹם שֶׁהֵם שִׁבְעָה שָׁבוּעוֹת בָּעֹמֶר"
    assert omer.count_line(49, "sefard", baomer=True).endswith("לָעֹמֶר")  # only an Ashkenaz custom


def test_every_night_has_text_in_every_nusach() -> None:
    for nusach in omer.NUSACHS:
        lines = {omer.count_line(n, nusach) for n in range(1, 50)}
        assert len(lines) == 49


def test_sefirah() -> None:
    assert omer.sefirah(1) == "חֶסֶד שֶׁבְּחֶסֶד"
    assert omer.sefirah(9) == "גְּבוּרָה שֶׁבִּגְבוּרָה"
    assert omer.sefirah(33) == "הוֹד שֶׁבְּהוֹד"
    assert omer.sefirah(49) == "מַלְכוּת שֶׁבְּמַלְכוּת"


def test_full_text() -> None:
    text = omer.full_text(33, "edot_hamizrach")
    assert text.startswith("בָּרוּךְ אַתָּה הַשֵּׁם אֱלֹקֵינוּ")  # no Divine Name from a speaker by default
    assert omer.count_line(33, "edot_hamizrach") in text and "הָרַחֲמָן" in text and text.endswith("הוֹד שֶׁבְּהוֹד.")
    assert "אֲדֹנָי אֱלֹהֵינוּ" in omer.full_text(33, full_name=True)
    assert "שֶׁבְּ" not in omer.full_text(33, "ashkenaz")  # Ashkenaz: no sefirah unless asked
    assert omer.full_text(33, "ashkenaz", with_sefirah=True).endswith("הוֹד שֶׁבְּהוֹד.")


@pytest.mark.parametrize(("n", "word"), [(1, "first"), (2, "second"), (12, "twelfth"), (20, "twentieth"),
                                         (21, "twenty-first"), (33, "thirty-third"), (49, "forty-ninth")])
def test_english_ordinal(n: int, word: str) -> None:
    assert omer.english_ordinal(n) == word


def test_simple_text() -> None:
    assert omer.simple_text(8) == "Tonight is the eighth night of the Omer."
    assert omer.simple_text(8, last_night=True) == (
        "Tonight is the eighth night of the Omer. Last night was the seventh night of the Omer.")
    assert omer.simple_text(1, last_night=True) == "Tonight is the first night of the Omer."
    assert omer.simple_text(2, "he", last_night=True) == (
        "הַלַּיְלָה סוֹפְרִים שְׁנֵי יָמִים לָעֹמֶר. אֶמֶשׁ סָפַרְנוּ יוֹם אֶחָד לָעֹמֶר.")


def test_announcement_styles() -> None:
    assert omer.announcement(8, {"style": "count"}) == omer.count_line(8)
    assert omer.announcement(8, {"style": "simple", "last_night": True}).startswith("Tonight is the eighth")
    assert omer.announcement(8, {"style": "full", "sefirah": False}).endswith("סֶלָה.")


def test_out_of_range() -> None:
    with pytest.raises(ValueError):
        omer.count_line(50)
    with pytest.raises(ValueError):
        omer.count_line(0)


def test_tts_call() -> None:
    players = ["media_player.kitchen"]
    assert tts_call({"engine_id": "tts.hila", "language": "he-IL", "voice": "he-IL-HilaNeural"}, players, "x") == (
        "tts", "speak", {"entity_id": "tts.hila", "media_player_entity_id": players, "message": "x", "cache": True,
                         "language": "he-IL", "options": {"voice": "he-IL-HilaNeural"}})
    assert tts_call({"engine_id": "google_translate", "language": "iw"}, players, "x") == (
        "tts", "google_translate_say", {"entity_id": players, "message": "x", "cache": True, "language": "iw"})


# ---------------------------------------------------------------- inside Home Assistant

# Thursday 2026-04-09, 16:00 New York: tonight is night 8; tomorrow (Friday) night 9 is Shabbat.
THURSDAY = datetime(2026, 4, 9, 16, 0, tzinfo=TZ)
SPEAKERS = ["media_player.kitchen", "media_player.dining"]


@pytest.fixture
async def manager(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> ShabbotManager:
    freezer.move_to(THURSDAY)
    await hass.config.async_set_time_zone("America/New_York")
    hass.config.latitude, hass.config.longitude, hass.config.elevation = 40.6501, -73.94958, 18
    assert await async_setup_component(hass, "homeassistant", {})
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    m: ShabbotManager = entry.runtime_data
    m.settings["dry_run"] = False
    m.config["omer"].update(enabled=True, players=SPEAKERS, time="tzeit+5m", style="count",
                            voices=[{"engine_id": "tts.hebrew", "language": "he-IL", "voice": None}])
    m.config_changed(reconcile=False)
    await hass.async_block_till_done()
    return m


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, to: datetime) -> None:
    freezer.move_to(to)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _tzeit(m: ShabbotManager, evening: date) -> datetime:
    from custom_components.shabbot.core import jcal  # noqa: PLC0415

    return jcal.Zmanim(evening, m.location, m.minhag).tzeit


async def test_announces_tonights_count(hass: HomeAssistant, freezer: FrozenDateTimeFactory,
                                        manager: ShabbotManager) -> None:
    calls = async_mock_service(hass, "tts", "speak")
    due = _tzeit(manager, THURSDAY.date()) + timedelta(minutes=5)
    assert manager.omer.next["night"] == 8
    assert datetime.fromisoformat(manager.omer.next["time"]) == due

    await _advance(hass, freezer, due - timedelta(seconds=30))
    assert calls == []
    await _advance(hass, freezer, due + timedelta(seconds=1))
    assert len(calls) == 1
    assert calls[0].data["entity_id"] == "tts.hebrew"
    assert calls[0].data["media_player_entity_id"] == SPEAKERS
    assert calls[0].data["message"] == omer.count_line(8)
    assert manager.omer.next["night"] == 9  # rescheduled for tomorrow


async def test_shabbat_night_announced_by_default_and_skippable(hass: HomeAssistant,
                                                                manager: ShabbotManager) -> None:
    season = {n["night"]: n for n in manager.omer.season()}
    assert season[9]["shabbat"] and season[9]["announce"]
    assert season[1]["holiday"] == "Pesach II" and season[1]["announce"]  # diaspora: second day of Pesach

    manager.config["omer"]["shabbat_yomtov"] = "skip"
    season = {n["night"]: n for n in manager.omer.season()}
    assert not season[9]["announce"] and not season[1]["announce"] and season[8]["announce"]

    # A per-night choice beats the default either way.
    manager.config["omer"]["nights"] = {"2026-04-10": "announce", "2026-04-09": "skip"}
    manager.omer.schedule()
    assert manager.omer.next["night"] == 9


async def test_dry_run_only_logs(hass: HomeAssistant, freezer: FrozenDateTimeFactory, manager: ShabbotManager) -> None:
    calls = async_mock_service(hass, "tts", "speak")
    manager.settings["dry_run"] = True
    await _advance(hass, freezer, datetime.fromisoformat(manager.omer.next["time"]) + timedelta(seconds=1))
    assert calls == []
    assert any(e["kind"] == "dry_run" and "Omer night 8" in e["message"] for e in manager.store.activity)


async def test_volume_and_two_voices(hass: HomeAssistant, freezer: FrozenDateTimeFactory,
                                     manager: ShabbotManager) -> None:
    speak = async_mock_service(hass, "tts", "speak")
    volume = async_mock_service(hass, "media_player", "volume_set")
    manager.config["omer"].update(volume=75, pause_s=0, voices=[
        {"engine_id": "tts.avri", "language": None, "voice": None},
        {"engine_id": "tts.hila", "language": None, "voice": None}])
    await manager.omer.async_announce(8, manager.config["omer"])
    assert volume[0].data["volume_level"] == 0.75
    assert [c.data["entity_id"] for c in speak] == ["tts.avri", "tts.hila"]
    assert manager.store.activity[-1]["kind"] == "omer"


async def test_websocket_save_and_season(hass: HomeAssistant, manager: ShabbotManager, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "shabbot/omer/save", "omer": {
        "enabled": True, "nusach": "ashkenaz", "style": "full", "time": "sunset+44m", "players": SPEAKERS,
        "voices": [{"engine_id": "tts.hebrew"}], "shabbat_yomtov": "skip"}})
    res = await client.receive_json()
    assert res["success"], res
    assert manager.config["omer"]["nusach"] == "ashkenaz" and manager.config["omer"]["time"] == "sunset+44m"

    await client.send_json_auto_id({"type": "shabbot/omer/season", "omer": {"style": "simple"}})
    res = await client.receive_json()
    nights = res["result"]["nights"]
    assert len(nights) == 49 and nights[7]["text"] == "Tonight is the eighth night of the Omer."
    assert res["result"]["tonight"]["night"] == 8

    await client.send_json_auto_id({"type": "shabbot/omer/save", "omer": {"time": "sunset+banana"}})
    assert not (await client.receive_json())["success"]

    await client.send_json_auto_id({"type": "shabbot/omer/save", "omer": {"enabled": True, "players": []}})
    assert not (await client.receive_json())["success"]

    await client.send_json_auto_id({"type": "shabbot/omer/preview", "expr": "tzeit+5m"})
    res = await client.receive_json()
    assert res["result"]["title"] == "Omer night 8" and res["result"]["time"].startswith("2026-04-09T")
