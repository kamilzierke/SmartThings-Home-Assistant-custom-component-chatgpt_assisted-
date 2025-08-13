
from __future__ import annotations
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import STCoordinator
from .entity import STCEntity

CAP = "thermostatCoolingSetpoint"
ATTR = "coolingSetpoint"
RANGE_ATTR = "coolingSetpointRange"

class STCSetpointNumber(STCEntity, NumberEntity):
    _attr_native_unit_of_measurement = "°C"
    _attr_native_step = 1.0

    @property
    def native_value(self):
        return self._current_attr()

    @property
    def native_min_value(self):
        rng = self._get_range()
        return float(rng[0]) if rng else 1.0

    @property
    def native_max_value(self):
        rng = self._get_range()
        return float(rng[1]) if rng else 30.0

    def _get_range(self):
        data = self.coordinator.data or {}
        caps = (data.get("components", {}).get(self._component_id, {}) or {}).get(CAP, {})
        payload = caps.get(RANGE_ATTR) or {}
        rng = payload.get("value")
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            return rng
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self._send(CAP, "setCoolingSetpoint", [value])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord: STCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    comps = (coord.data or {}).get("components") or {}

    for comp_id, caps in comps.items():
        if CAP in caps and ATTR in caps[CAP]:
            name = f"ST {comp_id} setpoint"
            uid = f"{coord.device_id}-{comp_id}-{CAP}-{ATTR}"
            entities.append(STCSetpointNumber(coord, comp_id, CAP, ATTR, name, uid))

    if entities:
        async_add_entities(entities, update_before_add=True)
