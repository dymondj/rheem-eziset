"""Water heater platform for rheem_eziset."""
from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import STATE_GAS, STATE_OFF, WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import STATE_BURNING
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator
from .entity import RheemEziSETEntity


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add water heater for passed config_entry in HA."""
    async_add_entities([RheemEziSETWaterHeater(entry.runtime_data, entry)])


class RheemEziSETWaterHeater(RheemEziSETEntity, WaterHeaterEntity):
    """rheem_eziset Water Heater class."""

    _attr_name = "Water Heater"
    _attr_operation_list = [STATE_GAS, STATE_OFF]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = PRECISION_WHOLE

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
    ) -> None:
        """Initialize the water heater."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}-water-heater"

    @property
    def current_operation(self) -> str:
        """Return gas if the burner is on."""
        if self.coordinator.data.get("state") == STATE_BURNING:
            return STATE_GAS
        return STATE_OFF

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature that can be set."""
        return self.coordinator.data.get("tempMin")

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature that can be set."""
        return self.coordinator.data.get("tempMax")

    @property
    def native_current_temperature(self) -> float | None:
        """Return the current temperature setting (the device does not report the actual water temperature)."""
        return self.coordinator.data.get("temp")

    @property
    def native_target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.coordinator.data.get("temp")

    async def _async_call_api(self, func, *args) -> None:
        """Run a blocking api call and then update the entities."""
        await self.hass.async_add_executor_job(func, *args)
        await self.coordinator.async_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature of the water heater."""
        await self._async_call_api(self.coordinator.api.set_temp, kwargs.get(ATTR_TEMPERATURE), self.min_temp, self.max_temp)

    async def async_start_bath_fill(self, temperature: int, volume: int) -> None:
        """Start a bath fill. The heater waits for the hot tap to be opened and stops the water at the volume."""
        await self._async_call_api(self.coordinator.api.start_bath_fill, temperature, volume)

    async def async_cancel_bath_fill(self) -> None:
        """Cancel or finish the bath fill started by Home Assistant."""
        await self._async_call_api(self.coordinator.api.cancel_bath_fill)

    async def async_set_heater_name(self, name: str) -> None:
        """Rename the heater."""
        await self._async_call_api(self.coordinator.api.set_heater_name, name)

    async def async_sync_time(self) -> None:
        """Send the current date and time to the heater."""
        await self._async_call_api(self.coordinator.api.sync_time, dt_util.now())
