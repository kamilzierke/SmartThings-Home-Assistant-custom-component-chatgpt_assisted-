from __future__ import annotations
from typing import Any, Iterable, Optional
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import STCoordinator
from .entity import STCEntity

# ---- helpers ----

def _iter_components(data: dict) -> Iterable[tuple[str, str, str]]:
    comps = (data or {}).get("components") or {}
    for comp_id, caps in comps.items():
        for cap_name, attrs in (caps or {}).items():
            for attr_name, payload in (attrs or {}).items():
                if isinstance(payload, dict) and "value" in payload:
                    yield comp_id, cap_name, attr_name

def _get_payload(coordinator: STCoordinator, comp_id: str, cap: str, attr: str) -> dict:
    """Zwraca surowy payload atrybutu (z polami value/unit/…) lub {}."""
    return (
        coordinator.data.get("components", {})
        .get(comp_id, {})
        .get(cap, {})
        .get(attr, {})
        or {}
    )

def _get_attr(coordinator: STCoordinator, comp_id: str, cap: str, attr: str) -> Any:
    return _get_payload(coordinator, comp_id, cap, attr).get("value")

def _norm_to_kwh(value: Optional[float], unit: str | None) -> Optional[float]:
    """Konwersja liczby do kWh w zależności od jednostki (Wh/kWh/None)."""
    if value is None:
        return None
    try:
        f = float(value)
    except Exception:
        return None
    if not unit:
        # Heurystyka: duże wartości zwykle Wh → zamień na kWh
        return f / 1000.0 if f > 500 else f
    u = unit.lower()
    if u in ("wh", "watt-hour", "watt_hour", "watt hours", "watt_hours"):
        return f / 1000.0
    # jeżeli to już kWh lub coś innego – zwracamy bez zmian
    return f

def _delta_wh_from_pcr(value: Any) -> Optional[float]:
    """
    Zwraca delta energii w Wh z payloadu powerConsumptionReport.powerConsumption.
    Akceptuje dict albo list[dict]; bierze ostatni rekord.
    """
    last = None
    if isinstance(value, list) and value:
        last = value[-1]
    elif isinstance(value, dict):
        last = value
    if not isinstance(last, dict):
        return None

    raw = last.get("deltaEnergy")
    unit = (last.get("deltaEnergyUnit") or last.get("unit") or "").lower()
    try:
        f = float(raw) if raw is not None else None
    except Exception:
        return None

    if f is None:
        return None
    # Normalizacja: jeśli SmartThings podał kWh → przelicz na Wh
    if unit in ("kwh", "kilo_watt_hour", "kilowatt-hour", "kilowatt_hour"):
        return f * 1000.0
    # Jeżeli unit brak lub Wh → traktuj jako Wh
    return f


def _parse_pcr(value: Any) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Parse powerConsumptionReport.powerConsumption into kWh/W:
    returns (energy_kwh, power_w, delta_kwh)
    Accepts dict or list[dict]; picks the last record.
    """
    last = None
    if isinstance(value, list) and value:
        last = value[-1]
    elif isinstance(value, dict):
        last = value
    if not isinstance(last, dict):
        return (None, None, None)

    def num(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    # ST bywa niespójne – sprawdzamy pola unit jeśli są
    energy_val = num(last.get("energy"))
    delta_val = num(last.get("deltaEnergy"))
    power_w = num(last.get("power"))
    energy_unit = (last.get("energyUnit") or last.get("unit") or last.get("energy_unit") or "") or None
    delta_unit = (last.get("deltaEnergyUnit") or last.get("unit") or last.get("delta_energy_unit") or "") or None

    energy_kwh = _norm_to_kwh(energy_val, energy_unit)
    delta_kwh = _norm_to_kwh(delta_val, delta_unit)

    return (energy_kwh, power_w, delta_kwh)

# ---- base entities ----

class STCSensor(STCEntity, SensorEntity):
    """Generic numeric sensor (returns raw value)."""
    @property
    def native_value(self):
        return self._current_attr()

# temperature
class STCTemperatureSensor(STCSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

# power W (MEASUREMENT)
class STCPowerSensor(STCSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

# ---- specialized PCR sensors (native_value computed each time) ----

class STCPcrBase(STCEntity, SensorEntity):
    """Base for powerConsumptionReport-derived sensors."""
    _role: str  # "energy_total" | "power" | "energy_delta"

    def __init__(self, *args, role: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._role = role

    @property
    def native_value(self):
        raw = _get_attr(self.coordinator, self._component_id,
                        "powerConsumptionReport", "powerConsumption")
        energy_kwh, power_w, delta_kwh = _parse_pcr(raw)
        if self._role == "energy_total":
            return energy_kwh  # kWh
        if self._role == "power":
            return power_w     # W
        if self._role == "energy_delta":
            return delta_kwh   # kWh
        return None

class STCPcrEnergyTotal(STCPcrBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

class STCPcrPower(STCPcrBase):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

class STCPcrEnergyDelta(STCPcrBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    # brak state_class – delta nie jest licznikiem

    @property
    def native_value(self):
        raw = _get_attr(
            self.coordinator, self._component_id,
            "powerConsumptionReport", "powerConsumption"
        )
        return _delta_wh_from_pcr(raw)  # Wh


# ---- energyMeter: total kWh with unit-aware conversion ----

class STCEnergyTotalFromEnergyMeter(STCEntity, SensorEntity):
    """Narastający licznik energii w kWh oparty o capability energyMeter.energy."""
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        payload = _get_payload(self.coordinator, self._component_id, "energyMeter", "energy")
        value = payload.get("value")
        unit = payload.get("unit")  # spodziewane "Wh" lub "kWh"
        return _norm_to_kwh(value, unit)

# ---- setup ----

TEMPERATURE_CAP = "temperatureMeasurement"
TEMPERATURE_ATTR = "temperature"

# capability/attribute handled elsewhere, so skip in generic section
NUMERIC_SKIP = {
    ("thermostatCoolingSetpoint", "coolingSetpoint"),
    ("powerConsumptionReport", "powerConsumption"),
    ("energyMeter", "energy"),
    ("powerMeter", "power"),
}

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord: STCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coord.data or {}
    entities: list[SensorEntity] = []

    # 1) Temperature
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) == (TEMPERATURE_CAP, TEMPERATURE_ATTR):
            name = f"ST {comp_id} temperature"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            entities.append(STCTemperatureSensor(coord, comp_id, cap, attr, name, uid))

    # 2) powerConsumptionReport.* → 3 encje (kWh/W)
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) == ("powerConsumptionReport", "powerConsumption"):
            entities.append(
                STCPcrEnergyTotal(
                    coord, comp_id, cap, attr,
                    f"ST {comp_id} energy total",
                    f"{coord.device_id}-{comp_id}-pcr-energy_total",
                    role="energy_total",
                )
            )
            entities.append(
                STCPcrPower(
                    coord, comp_id, cap, attr,
                    f"ST {comp_id} power",
                    f"{coord.device_id}-{comp_id}-pcr-power",
                    role="power",
                )
            )
            entities.append(
                STCPcrEnergyDelta(
                    coord, comp_id, cap, attr,
                    f"ST {comp_id} energy delta",
                    f"{coord.device_id}-{comp_id}-pcr-energy_delta",
                    role="energy_delta",
                )
            )

    # 3) energyMeter.energy → total kWh
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) == ("energyMeter", "energy"):
            name = f"ST {comp_id} energy"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            entities.append(STCEnergyTotalFromEnergyMeter(coord, comp_id, cap, attr, name, uid))

    # 4) powerMeter.power (W)
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) == ("powerMeter", "power"):
            name = f"ST {comp_id} power"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            entities.append(STCPowerSensor(coord, comp_id, cap, attr, name, uid))

    # 5) Generic numeric sensors
    for comp_id, cap, attr in _iter_components(data):
        if (cap, attr) in NUMERIC_SKIP or (cap, attr) == (TEMPERATURE_CAP, TEMPERATURE_ATTR):
            continue
        val = _get_attr(coord, comp_id, cap, attr)
        if isinstance(val, (int, float)):
            name = f"ST {comp_id} {cap}.{attr}"
            uid = f"{coord.device_id}-{comp_id}-{cap}-{attr}"
            entities.append(STCSensor(coord, comp_id, cap, attr, name, uid))

    if entities:
        async_add_entities(entities, update_before_add=True)
