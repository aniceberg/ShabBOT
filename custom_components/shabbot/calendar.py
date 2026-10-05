"""Calendars: Issur Melacha periods, and the routines scheduled in them."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ShabbotConfigEntry
from .core import jcal, planner
from .entity import ShabbotEntity


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([IssurMelachaCalendar(entry.runtime_data), RoutinesCalendar(entry.runtime_data)])


def _block_event(b: jcal.Block) -> CalendarEvent:
    return CalendarEvent(start=b.start, end=b.end, summary=b.title, uid=f"block-{b.id}",
                         description=f"Candle lighting {b.start:%-I:%M %p} · Havdalah {b.end:%-I:%M %p}")


def _instance_event(i: planner.Instance) -> CalendarEvent:
    lines = []
    for a in i.actions:
        if a.disabled or a.error or not a.start or not a.end:
            continue
        lines.append(f"{a.entity_id}: {a.state} {a.start:%-I:%M %p}–{a.end:%-I:%M %p}")
    return CalendarEvent(start=i.start, end=i.end, uid=f"routine-{i.target.key}",
                         summary=f"{i.routine['name']} · {i.target.title}", description="\n".join(lines))


class IssurMelachaCalendar(ShabbotEntity, CalendarEntity):
    _attr_icon = "mdi:calendar-star"

    def __init__(self, manager) -> None:
        super().__init__(manager, "issur_melacha_calendar")

    @property
    def event(self) -> CalendarEvent | None:
        blocks = self.manager.upcoming_blocks(14)
        return _block_event(blocks[0]) if blocks else None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime,
                               end_date: datetime) -> list[CalendarEvent]:
        blocks, _ = self.manager.plan(start_date.date() - timedelta(days=1), end_date.date())
        return [_block_event(b) for b in blocks if b.end > start_date and b.start < end_date]


class RoutinesCalendar(ShabbotEntity, CalendarEntity):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, manager) -> None:
        super().__init__(manager, "routines_calendar")

    @property
    def event(self) -> CalendarEvent | None:
        now = self.manager.now()
        upcoming = sorted((i for i in self.manager.instances if i.routine and i.end > now), key=lambda i: i.start)
        return _instance_event(upcoming[0]) if upcoming else None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime,
                               end_date: datetime) -> list[CalendarEvent]:
        _, instances = self.manager.plan(start_date.date() - timedelta(days=1), end_date.date())
        return [_instance_event(i) for i in instances
                if i.routine and i.end > start_date and i.start < end_date]
