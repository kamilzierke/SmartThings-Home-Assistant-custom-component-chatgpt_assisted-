
from __future__ import annotations
from typing import Any
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import STCoordinator

class STCEntity(CoordinatorEntity[STCoordinator]):
    _attr_should_poll = False

    def __init__(self, coordinator: STCoordinator, component_id: str, capability: str, attribute: str, name: str, unique_id: str):
        super().__init__(coordinator)
        self._component_id = component_id
        self._capability = capability
        self._attribute = attribute
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def extra_state_attributes(self):
        return {
            "st_component": self._component_id,
            "st_capability": self._capability,
            "st_attribute": self._attribute,
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_id)},
            name="SmartThings Device",
            manufacturer="SmartThings",
        )

    def _current_attr(self) -> Any:
        data = self.coordinator.data or {}
        comps = data.get("components") or {}
        comp = comps.get(self._component_id) or {}
        cap = comp.get(self._capability) or {}
        attr = cap.get(self._attribute) or {}
        return attr.get("value")

    async def _send(self, capability: str, command: str, arguments=None):
        await self.coordinator.command(self._component_id, capability, command, arguments or [])
