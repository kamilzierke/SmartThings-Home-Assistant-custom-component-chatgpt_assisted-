
from __future__ import annotations
from datetime import timedelta
from typing import Any
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import STApiClient

_LOGGER = logging.getLogger(__name__)

class STCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, token: str, device_id: str, scan_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name="st_components",
            update_interval=timedelta(seconds=max(10, int(scan_interval))),
        )
        self._device_id = device_id
        self._client = STApiClient(async_get_clientsession(hass), token)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._client.get_status(self._device_id)
            return data or {}
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    @property
    def device_id(self) -> str:
        return self._device_id

    async def command(self, component: str, capability: str, command: str, arguments=None) -> dict:
        return await self._client.send_command(self._device_id, component, capability, command, arguments or [])
