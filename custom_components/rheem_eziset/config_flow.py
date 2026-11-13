"""Adds config flow for Rheem EziSET."""
from __future__ import annotations

import traceback

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.core import callback

from .api import RheemEziSETApi
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .discovery import async_discover


class RheemEziSETConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for rheem_eziset."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow with no errors."""
        self._errors: dict[str, str] = {}
        self._discovered: dict[str, str] | None = None

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()

            # Don't allow duplicates
            for entry in self._async_current_entries():
                if host in (entry.title, entry.data.get(CONF_HOST)):
                    return self.async_abort(reason="host_already_exists")

            # Test connectivity
            if await self._test_host(host):
                data = {CONF_HOST: host}
                # The MAC address is only known if the device answers a discovery request.
                for mac, address in (await async_discover(self.hass, host=host)).items():
                    if address == host:
                        await self.async_set_unique_id(mac)
                        self._abort_if_unique_id_configured()
                        data[CONF_MAC] = mac
                return self.async_create_entry(title=host, data=data)

            self._errors["base"] = "connection"
            return self._show_config_form(host)

        if self._discovered is None:
            configured = {entry.data.get(CONF_HOST) for entry in self._async_current_entries()}
            self._discovered = {mac: address for mac, address in (await async_discover(self.hass)).items() if address not in configured}

        return self._show_config_form(next(iter(self._discovered.values()), None))

    def _show_config_form(self, host: str | None) -> ConfigFlowResult:
        """Show the form, suggesting the address of a discovered device if there is one."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, description={"suggested_value": host}): str}),
            errors=self._errors,
        )

    async def _test_host(self, host: str) -> bool:
        """Validate host."""
        try:
            api = RheemEziSETApi(host=host)
            await self.hass.async_add_executor_job(api.get_data)
            return True
        except Exception as ex:  # pylint: disable=broad-except
            LOGGER.error(
                "%s Exception in connection: %s - traceback: %s",
                DOMAIN,
                ex,
                traceback.format_exc(),
            )
        return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Options flow for Rheem EziSET."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle an option flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, description={"suggested_value": current}): vol.All(vol.Coerce(int), vol.Range(min=1)),
                }
            ),
        )
