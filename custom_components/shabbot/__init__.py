"""ShabBOT: Shabbat & Yom Tov automation for Home Assistant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, NAME, PANEL_COMPONENT, PANEL_ICON, PANEL_STATIC_URL, PANEL_URL, VERSION
from .manager import ShabbotManager
from .services import async_setup_services
from .store import ShabbotStore
from .websocket import async_setup_websocket

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]
FRONTEND_DIR = Path(__file__).parent / "frontend"
STATIC_DIR = Path(__file__).parent / "static"


def _asset_url(base: str, path: Path) -> str:
    """Cache-busting URL: changes with each release and each rebuild of the file."""
    try:
        stamp = int(path.stat().st_mtime)
    except OSError:
        stamp = 0
    return f"{base}?v={VERSION}-{stamp}"


# Computed at import (which HA runs off the event loop), so no file I/O happens inside the loop.
ICONS_URL = _asset_url(f"{PANEL_STATIC_URL}_icons/shabbot-icons.js", STATIC_DIR / "shabbot-icons.js")
PANEL_MODULE_URL = _asset_url(f"{PANEL_STATIC_URL}/shabbot-panel.js", FRONTEND_DIR / "shabbot-panel.js")
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ShabbotConfigEntry = ConfigEntry[ShabbotManager]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    async_setup_websocket(hass)
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ShabbotConfigEntry) -> bool:
    store = ShabbotStore(hass)
    await store.async_load(dict(entry.data))
    manager = ShabbotManager(hass, entry, store)
    entry.runtime_data = manager
    hass.data[DOMAIN] = manager

    await _async_register_panel(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if hass.state is CoreState.running:
        await manager.async_start()
    else:
        async def _start(_event: Event) -> None:
            await manager.async_start()

        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _start))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShabbotConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
        frontend.async_remove_panel(hass, PANEL_URL)
        frontend.remove_extra_js_url(hass, ICONS_URL)
        hass.data.pop(DOMAIN, None)
    return unloaded


async def _async_register_panel(hass: HomeAssistant) -> None:
    if not hass.data.get(f"{DOMAIN}_static"):
        await hass.http.async_register_static_paths([
            StaticPathConfig(PANEL_STATIC_URL, str(FRONTEND_DIR), cache_headers=False),
            StaticPathConfig(f"{PANEL_STATIC_URL}_icons", str(STATIC_DIR), cache_headers=False),
        ])
        hass.data[f"{DOMAIN}_static"] = True
    # Registers the "shabbot:logo" icon on every frontend page so the sidebar can show it.
    frontend.add_extra_js_url(hass, ICONS_URL)
    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        return
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL,
        module_url=PANEL_MODULE_URL,
        sidebar_title=NAME,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        config={},
        embed_iframe=False,
    )
