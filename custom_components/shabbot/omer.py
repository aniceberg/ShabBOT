"""Sefirat Haomer reminder: schedules the nightly announcement and speaks it with a TTS engine."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.event import async_track_point_in_time

from .core import jcal, omer, timeexpr

if TYPE_CHECKING:
    from .manager import ShabbotManager

SERVICE_TIMEOUT = 60


def evening_anchors(evening: date, m: ShabbotManager) -> dict[str, datetime]:
    """Zmanim for the evening the Omer is counted (the civil date's sunset, tzeit, …)."""
    z = jcal.Zmanim(evening, m.location, m.minhag)
    nxt = evening + timedelta(days=1)
    return {**z.anchors(), "midnight": datetime(nxt.year, nxt.month, nxt.day, tzinfo=m.location.tzinfo)}


def announce_time(evening: date, expr: str, m: ShabbotManager) -> datetime:
    """When the reminder for this evening goes off. Clock times before noon are the next morning."""
    return timeexpr.evaluate(expr, evening_anchors(evening, m), evening, True, m.location.tzinfo)


def night_info(evening: date, cfg: dict[str, Any], m: ShabbotManager) -> dict[str, Any] | None:
    """Everything the panel shows about one evening of the Omer, or None outside the Omer."""
    n = omer.omer_night(evening)
    if n is None:
        return None
    israel = m.minhag.israel
    day = evening + timedelta(days=1)  # the Jewish day that starts this evening
    holiday = jcal.yom_tov(day, israel)
    shabbat = day.weekday() == 5
    choice = (cfg.get("nights") or {}).get(evening.isoformat())
    if choice in ("announce", "skip"):
        announce = choice == "announce"
    else:
        announce = not ((shabbat or holiday) and cfg.get("shabbat_yomtov") == "skip")
    try:
        when, error = announce_time(evening, cfg.get("time") or "", m).isoformat(), None
    except timeexpr.ExprError as err:
        when, error = None, str(err)
    return {
        "evening": evening.isoformat(),
        "night": n,
        "time": when,
        "error": error,
        "shabbat": shabbat,
        "holiday": holiday.name if holiday else None,
        "announce": announce,
        "choice": choice,
        "text": omer.announcement(n, cfg),
    }


class OmerAnnouncer:
    """Keeps one timer for the next Omer announcement."""

    def __init__(self, m: ShabbotManager) -> None:
        self.m = m
        self._unsub: CALLBACK_TYPE | None = None
        self.next: dict[str, Any] | None = None  # night_info of the scheduled announcement

    @property
    def cfg(self) -> dict[str, Any]:
        return self.m.config["omer"]

    def season(self, cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """This year's 49 nights (or next year's, once this year's are over)."""
        cfg = cfg or self.cfg
        today = self.m.now().date()
        return [info for d in omer.omer_season(today - timedelta(days=1))
                if (info := night_info(d, cfg, self.m)) is not None]

    def next_due(self, after: datetime) -> dict[str, Any] | None:
        if not self.cfg.get("enabled"):
            return None
        start = after.astimezone(self.m.location.tzinfo).date() - timedelta(days=1)
        for _ in range(2):  # this season, then next year's if this one is over
            for info in (night_info(d, self.cfg, self.m) for d in omer.omer_season(start)):
                if info and info["announce"] and info["time"] and datetime.fromisoformat(info["time"]) > after:
                    return info
            start = omer.omer_season(start)[-1] + timedelta(days=1)
        return None

    @callback
    def schedule(self) -> None:
        self.cancel()
        self.next = self.next_due(self.m.now())
        if self.next:
            self._unsub = async_track_point_in_time(self.m.hass, self._fire, datetime.fromisoformat(self.next["time"]))

    @callback
    def cancel(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _fire(self, _now: datetime) -> None:
        self._unsub = None
        info = self.next
        if info:
            self.m.hass.async_create_task(self.async_announce(info["night"], self.cfg))
        self.schedule()

    async def async_announce(self, n: int, cfg: dict[str, Any], force: bool = False) -> None:
        """Speak night `n` on the configured speakers. `force` (the panel's Test button) ignores dry run."""
        m = self.m
        text = omer.announcement(n, cfg)
        players = list(cfg.get("players") or [])
        voices = [v for v in cfg.get("voices") or [] if v.get("engine_id")]
        label = f"Omer night {n}"
        if not players or not voices:
            m.log("error", f"{label}: choose at least one speaker and a text-to-speech engine")
            return
        if m.settings.get("dry_run") and not force:
            m.log("dry_run", f"Would announce {label} on {', '.join(players)}: {text}")
            return
        try:
            async with asyncio.timeout(SERVICE_TIMEOUT + len(voices) * float(cfg.get("pause_s") or 0)):
                if cfg.get("volume") is not None:
                    await m.hass.services.async_call("media_player", "volume_set", {
                        "entity_id": players, "volume_level": round(float(cfg["volume"]) / 100, 2)}, blocking=True)
                for i, voice in enumerate(voices):
                    if i:
                        await asyncio.sleep(float(cfg.get("pause_s") or 0))
                    domain, service, data = tts_call(voice, players, text)
                    await m.hass.services.async_call(domain, service, data, blocking=True)
        except Exception as err:  # noqa: BLE001 - a speaker failure must not stop the engine
            m.log("error", f"{label}: announcement failed: {err}")
            return
        m.log("omer", f"Announced {label}{' (test)' if force else ''}: {text}")


def tts_call(voice: dict[str, Any], players: list[str], text: str) -> tuple[str, str, dict[str, Any]]:
    """The service call that speaks `text`: `tts.speak` for TTS entities, `tts.<engine>_say` for legacy engines."""
    engine = voice["engine_id"]
    if engine.startswith("tts."):
        service = "speak"
        data: dict[str, Any] = {"entity_id": engine, "media_player_entity_id": players}
    else:
        service = f"{engine}_say"
        data = {"entity_id": players}
    data.update(message=text, cache=True)
    if voice.get("language"):
        data["language"] = voice["language"]
    if voice.get("voice"):
        data["options"] = {"voice": voice["voice"]}
    return "tts", service, data
