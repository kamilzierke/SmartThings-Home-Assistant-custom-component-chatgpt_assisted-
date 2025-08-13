"""Config flow for SmartThings Components integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_STALE_AFTER_S,
    CONF_COOLDOWN_AFTER_429_S,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_AFTER_S,
    DEFAULT_COOLDOWN_AFTER_429_S,
)


class STConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartThings Components."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            device_id = user_input[CONF_DEVICE_ID].strip()
            scan_interval = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

            return self.async_create_entry(
                title=f"ST device {device_id}",
                data={
                    CONF_TOKEN: token,
                    CONF_DEVICE_ID: device_id,
                    CONF_SCAN_INTERVAL: scan_interval,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return STOpsFlowHandler(config_entry)


class STOpsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SmartThings Components."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry  # używamy polecanego wzorca

    async def async_step_init(self, user_input=None):
        entry = self.config_entry

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                    CONF_STALE_AFTER_S: int(user_input.get(CONF_STALE_AFTER_S, DEFAULT_STALE_AFTER_S)),
                    CONF_COOLDOWN_AFTER_429_S: int(
                        user_input.get(CONF_COOLDOWN_AFTER_429_S, DEFAULT_COOLDOWN_AFTER_429_S)
                    ),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                ): int,
                vol.Optional(
                    CONF_STALE_AFTER_S,
                    default=entry.options.get(CONF_STALE_AFTER_S, DEFAULT_STALE_AFTER_S),
                ): int,
                vol.Optional(
                    CONF_COOLDOWN_AFTER_429_S,
                    default=entry.options.get(CONF_COOLDOWN_AFTER_429_S, DEFAULT_COOLDOWN_AFTER_429_S),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
