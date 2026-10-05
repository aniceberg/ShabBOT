"""Global switches: device protection, and dry-run (log only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ShabbotConfigEntry
from .entity import ShabbotEntity


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    m = entry.runtime_data
    async_add_entities([SettingSwitch(m, "protection", "mdi:shield-home"),
                        SettingSwitch(m, "dry_run", "mdi:test-tube")])


class SettingSwitch(ShabbotEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager, key: str, icon: str) -> None:
        super().__init__(manager, key)
        self._key = key
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(self.manager.settings.get(self._key))

    async def _set(self, value: bool) -> None:
        self.manager.settings[self._key] = value
        self.manager.log("settings", f"{self._key.replace('_', ' ').capitalize()} turned {'on' if value else 'off'}")
        self.manager.config_changed()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
