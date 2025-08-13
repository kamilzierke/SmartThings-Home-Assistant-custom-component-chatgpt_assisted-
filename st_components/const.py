from homeassistant.const import Platform

DOMAIN = "st_components"

CONF_TOKEN = "token"
CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_STALE_AFTER_S = "stale_after_s"
CONF_COOLDOWN_AFTER_429_S = "cooldown_after_429_s"

DEFAULT_SCAN_INTERVAL = 30
DEFAULT_STALE_AFTER_S = 180
DEFAULT_COOLDOWN_AFTER_429_S = 360

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]
