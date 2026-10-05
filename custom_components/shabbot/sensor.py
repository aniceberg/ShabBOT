"""Next candle lighting / havdalah, and active overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ShabbotConfigEntry
from .core import jcal
from .entity import ShabbotEntity


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    m = entry.runtime_data
    async_add_entities([NextCandleLighting(m), NextHavdalah(m), ActiveOverrides(m)])


class NextCandleLighting(ShabbotEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:candle"

    def __init__(self, manager) -> None:
        super().__init__(manager, "next_candle_lighting")

    def _next(self) -> jcal.Slot | None:
        now = self.manager.now()
        nights = [s for b in self.manager.upcoming_blocks() for s in b.slots
                  if s.part is jcal.Part.NIGHT and s.start > now]
        return min(nights, key=lambda s: s.start) if nights else None

    @property
    def native_value(self) -> datetime | None:
        slot = self._next()
        return slot.start if slot else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        slot = self._next()
        return {"title": slot.title} if slot else {}


class NextHavdalah(ShabbotEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:weather-night"

    def __init__(self, manager) -> None:
        super().__init__(manager, "next_havdalah")

    @property
    def native_value(self) -> datetime | None:
        now = self.manager.now()
        ends = [b.end for b in self.manager.upcoming_blocks() if b.end > now]
        return min(ends) if ends else None


class ActiveOverrides(ShabbotEntity, SensorEntity):
    _attr_icon = "mdi:hand-back-right"

    def __init__(self, manager) -> None:
        super().__init__(manager, "active_overrides")

    @property
    def native_value(self) -> int:
        return len(self.manager.overrides)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"overrides": self.manager.overrides, "paused": self.manager.paused}
