"""Mode select: Normal, or one of the configured Summer/Vacation modes."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ShabbotConfigEntry
from .core import planner
from .entity import ShabbotEntity

NORMAL = "Normal"


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ModeSelect(entry.runtime_data)])


class ModeSelect(ShabbotEntity, SelectEntity):
    _attr_icon = "mdi:home-switch"

    def __init__(self, manager) -> None:
        super().__init__(manager, "mode")

    @property
    def options(self) -> list[str]:
        return [NORMAL, *[m["name"] for m in self.manager.config["modes"]]]

    @property
    def current_option(self) -> str:
        mode = planner.active_mode(self.manager.config["modes"], self.manager.now().date())
        return mode["name"] if mode else NORMAL

    async def async_select_option(self, option: str) -> None:
        """Choosing a mode starts it today, open-ended; Normal ends any active mode yesterday."""
        today = self.manager.now().date()
        for mode in self.manager.config["modes"]:
            if mode["name"] == option:
                mode.update(enabled=True, start=today.isoformat(), end=None)
            elif planner.active_mode([mode], today) is not None:
                if mode["start"] >= today.isoformat():
                    mode["enabled"] = False
                else:
                    mode["end"] = (today - timedelta(days=1)).isoformat()
        self.manager.config_changed()
