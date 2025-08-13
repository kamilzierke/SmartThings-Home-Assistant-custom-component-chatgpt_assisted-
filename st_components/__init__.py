from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_TOKEN,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_STALE_AFTER_S,
    CONF_COOLDOWN_AFTER_429_S,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_AFTER_S,
    DEFAULT_COOLDOWN_AFTER_429_S,
)
from .coordinator import STCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    token = entry.data[CONF_TOKEN]
    device_id = entry.data[CONF_DEVICE_ID]

    scan = int(entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))
    stale = int(entry.options.get(CONF_STALE_AFTER_S, DEFAULT_STALE_AFTER_S))
    cooldown = int(entry.options.get(CONF_COOLDOWN_AFTER_429_S, DEFAULT_COOLDOWN_AFTER_429_S))

    coord = STCoordinator(
        hass,
        token=token,
        device_id=device_id,
        scan_interval=scan,
        stale_after_s=stale,
        cooldown_after_429_s=cooldown,
    )
    hass.data[DOMAIN][entry.entry_id] = coord

    await coord.async_config_entry_first_refresh()

    async def _options_updated(hass: HomeAssistant, updated_entry: ConfigEntry):
        new_scan = int(updated_entry.options.get(CONF_SCAN_INTERVAL, updated_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))
        new_stale = int(updated_entry.options.get(CONF_STALE_AFTER_S, DEFAULT_STALE_AFTER_S))
        new_cooldown = int(updated_entry.options.get(CONF_COOLDOWN_AFTER_429_S, DEFAULT_COOLDOWN_AFTER_429_S))
        coord.update_options(new_scan, new_stale, new_cooldown)
        _LOGGER.debug(
            "st_components options updated: scan=%s stale_after=%s cooldown_429=%s",
            new_scan, new_stale, new_cooldown
        )

    entry.async_on_unload(entry.add_update_listener(_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
