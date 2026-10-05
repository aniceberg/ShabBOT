"""Issur Melacha in effect."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ShabbotConfigEntry
from .entity import ShabbotEntity


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([IssurMelachaSensor(entry.runtime_data)])


class IssurMelachaSensor(ShabbotEntity, BinarySensorEntity):
    _attr_icon = "mdi:candle"

    def __init__(self, manager) -> None:
        super().__init__(manager, "issur_melacha")

    @property
    def is_on(self) -> bool:
        return self.manager.current_block() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        block = self.manager.current_block()
        if block is None:
            return {}
        return {"title": block.title, "start": block.start.isoformat(), "end": block.end.isoformat()}
