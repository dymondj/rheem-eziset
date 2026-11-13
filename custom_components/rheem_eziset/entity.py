"""Sets up the basic entity template."""
from __future__ import annotations

from homeassistant.const import CONF_MAC
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator


class RheemEziSETEntity(CoordinatorEntity[RheemEziSETDataUpdateCoordinator]):
    """Basic entity definition used by all entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RheemEziSETDataUpdateCoordinator, entry: RheemEziSETConfigEntry) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Defines the device information."""
        info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api.host)},
            name=self.coordinator.data.get("heaterName", NAME),
            manufacturer=MANUFACTURER,
            sw_version=self.coordinator.data.get("FWversion"),
        )
        if mac := self.entry.data.get(CONF_MAC):
            info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}
        return info

    @property
    def available(self) -> bool:
        """
        Returns the availability of the device.

        Powerline comms are noisy, so the device is only unavailable once several successive requests have failed.
        """
        return self.coordinator.last_update_success or not self.coordinator.problem_flag
