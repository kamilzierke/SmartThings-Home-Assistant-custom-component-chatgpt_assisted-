
from __future__ import annotations
from typing import Any, Iterable
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import STCoordinator
from .entity import STCEntity

TEMPERATURE_CAP = "temperatureMeasurement"
TEMPERATURE_ATTR = "temperature"

NUMERIC_SKIP = {
    ("thermostatCoolingSetpoint", "coolingSetpoint"),
}

def _iter_components(data: dict) -> Iterable[tuple[str, str, str]]:
    comps = (data or {}).get("components") or {}
    for comp_id, caps in comps.items():
        for cap_name, attrs in (caps or {}).items():
            for attr_name, payload in (attrs or {}).items():
                if isinstance(payload, dict) and "value" in payload:
                    yield comp_id, cap_name, attr_name

class STCSensor(STCEntity, SensorEntity):
    @property
    def native_value(self):
        return self._current_attr()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord: STCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coord.data or {}
    entities: list[SensorEntity] = []

    # 1) temperature sensors
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) == (TEMPERATURE_CAP, TEMPERATURE_ATTR):
            name = f"ST {comp_id} temperature"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            ent = STCSensor(coord, comp_id, cap, attr, name, uid)
            ent._attr_device_class = "temperature"
            ent._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            entities.append(ent)

    # 2) generic numeric sensors for other numeric attributes
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) in NUMERIC_SKIP or (cap, attr) == (TEMPERATURE_CAP, TEMPERATURE_ATTR):
            continue
        payload = (coord.data.get("components", {}).get(comp_id, {}).get(cap, {}).get(attr, {}) or {})
        val = payload.get("value")
        if isinstance(val, (int, float)):
            name = f"ST {comp_id} {cap}.{attr}"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            entities.append(STCSensor(coord, comp_id, cap, attr, name, uid))

    if entities:
        async_add_entities(entities, update_before_add=True)
