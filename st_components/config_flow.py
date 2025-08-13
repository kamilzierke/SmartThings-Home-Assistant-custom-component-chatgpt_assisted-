
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_TOKEN, CONF_DEVICE_ID, CONF_SCAN_INTERVAL

class STConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            token = user_input.get(CONF_TOKEN, "").strip()
            device_id = user_input.get(CONF_DEVICE_ID, "").strip()
            if not token:
                errors["base"] = "token_missing"
            elif not device_id:
                errors["base"] = "device_id_missing"
            else:
                # store provided values; token may or may not start with Bearer
                data = {
                    CONF_TOKEN: token,
                    CONF_DEVICE_ID: device_id,
                    CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, 30)),
                }
                return self.async_create_entry(title=f"ST device {device_id}", data=data)

        data_schema = vol.Schema({
            vol.Required(CONF_TOKEN): str,
            vol.Required(CONF_DEVICE_ID): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=30): int,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return STOpsFlowHandler(config_entry)

class STOpsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # store options only (HA will keep data unchanged)
            return self.async_create_entry(title="", data={
                CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, 30))
            })
        data_schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, 30))): int,
        })
        return self.async_show_form(step_id="init", data_schema=data_schema)
