
from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import STCoordinator
from .entity import STCEntity

class STCPowerModeSwitch(STCEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        val = self._current_attr()
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("on", "active", "true")
        return bool(val)

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(self._capability, "activate", [])

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(self._capability, "deactivate", [])

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord: STCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    comps = (coord.data or {}).get("components") or {}

    for comp_id, caps in comps.items():
        for cap_name, attrs in (caps or {}).items():
            if cap_name.endswith("powerCool") or cap_name.endswith("powerFreeze"):
                # choose an attribute carrying state if exists
                attr_name = next(iter(attrs.keys()), "state")
                name = f"ST {comp_id} {cap_name}"
                uid = f"{coord.device_id}-{comp_id}-{cap_name}-{attr_name}"
                entities.append(STCPowerModeSwitch(coord, comp_id, cap_name, attr_name, name, uid))

    if entities:
        async_add_entities(entities, update_before_add=True)
