
from __future__ import annotations
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS, CONF_TOKEN, CONF_DEVICE_ID, CONF_SCAN_INTERVAL
from .coordinator import STCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    token = entry.data[CONF_TOKEN]
    device_id = entry.data[CONF_DEVICE_ID]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 30))
    coord = STCoordinator(hass, token, device_id, scan_interval)
    await coord.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coord

    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry):
        new_scan = updated_entry.options.get(CONF_SCAN_INTERVAL, updated_entry.data.get(CONF_SCAN_INTERVAL, 30))
        coord.update_interval = timedelta(seconds=max(10, int(new_scan)))
        _LOGGER.debug("st_components: update_interval set to %ss", new_scan)

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
