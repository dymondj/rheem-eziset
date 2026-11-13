"""
Custom integration to integrate rheem_eziset with Home Assistant.

For more details about this integration, please refer to
https://github.com/illuzn/rheem-eziset/
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.water_heater import DOMAIN as WATER_HEATER_DOMAIN
from homeassistant.const import ATTR_TEMPERATURE, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.typing import ConfigType

from .api import RheemEziSETApi
from .const import (
    ATTR_VOLUME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HEATER_NAME_MAX_LENGTH,
    LOGGER,
    PLATFORMS,
    SERVICE_CANCEL_BATH_FILL,
    SERVICE_SET_HEATER_NAME,
    SERVICE_START_BATH_FILL,
    SERVICE_SYNC_TIME,
)
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the services provided by this integration."""
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_START_BATH_FILL,
        entity_domain=WATER_HEATER_DOMAIN,
        schema={
            vol.Required(ATTR_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(ATTR_VOLUME): vol.All(vol.Coerce(int), vol.Range(min=1)),
        },
        func="async_start_bath_fill",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_CANCEL_BATH_FILL,
        entity_domain=WATER_HEATER_DOMAIN,
        schema=None,
        func="async_cancel_bath_fill",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_HEATER_NAME,
        entity_domain=WATER_HEATER_DOMAIN,
        schema={vol.Required(CONF_NAME): vol.All(cv.string, vol.Length(min=1, max=HEATER_NAME_MAX_LENGTH))},
        func="async_set_heater_name",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SYNC_TIME,
        entity_domain=WATER_HEATER_DOMAIN,
        schema=None,
        func="async_sync_time",
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry) -> bool:
    """Set up this integration using UI."""
    LOGGER.debug(
        "Setting up entry for device: %s",
        entry.title,
    )

    api = RheemEziSETApi(host=entry.data[CONF_HOST])
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = RheemEziSETDataUpdateCoordinator(hass, entry=entry, api=api, update_interval=scan_interval)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))  # Reload the entry on configuration changes.

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
