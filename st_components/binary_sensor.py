
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import STCoordinator
from .entity import STCEntity

CONTACT_CAP = "contactSensor"
CONTACT_ATTR = "contact"

class STCBinarySensor(STCEntity, BinarySensorEntity):
    def __init__(self, *args, device_class: BinarySensorDeviceClass | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._attr_device_class = device_class

    @property
    def is_on(self):
        val = self._current_attr()
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("on", "open", "detected", "true")
        return bool(val)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord: STCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    comps = (coord.data or {}).get("components") or {}

    for comp_id, caps in comps.items():
        # contact sensor
        if CONTACT_CAP in caps and CONTACT_ATTR in caps[CONTACT_CAP]:
            name = f"ST {comp_id} contact"
            uid = f"{coord.device_id}-{comp_id}-{CONTACT_CAP}-{CONTACT_ATTR}"
            entities.append(STCBinarySensor(coord, comp_id, CONTACT_CAP, CONTACT_ATTR, name, uid, device_class=BinarySensorDeviceClass.DOOR))

        # any boolean-like attribute as a binary sensor
        for cap_name, attrs in (caps or {}).items():
            for attr_name, payload in (attrs or {}).items():
                if isinstance(payload, dict) and "value" in payload:
                    val = payload.get("value")
                    if isinstance(val, bool):
                        name = f"ST {comp_id} {cap_name}.{attr_name}"
                        uid = f"{coord.device_id}-{comp_id}-{cap_name}-{attr_name}"
                        entities.append(STCBinarySensor(coord, comp_id, cap_name, attr_name, name, uid))

    if entities:
        async_add_entities(entities, update_before_add=True)
