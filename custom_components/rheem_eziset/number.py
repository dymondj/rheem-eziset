"""Number platform for rheem_eziset."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ICON_TIMER, SESSION_TIMER_MAX, SESSION_TIMER_MIN
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator
from .entity import RheemEziSETEntity


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add number for passed config_entry in HA."""
    async_add_entities([RheemEziSETNumber(entry.runtime_data, entry)])


class RheemEziSETNumber(RheemEziSETEntity, NumberEntity):
    """rheem_eziset Number class."""

    _attr_native_min_value = SESSION_TIMER_MIN
    _attr_native_max_value = SESSION_TIMER_MAX
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = ICON_TIMER
    _attr_name = "Session Timeout"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}-number"

    @property
    def native_value(self):
        """Return the session timer."""
        return self.coordinator.data.get("sessionTimer")

    async def async_set_native_value(self, value: float) -> None:
        """Set the session timer of the water heater."""
        await self.hass.async_add_executor_job(self.coordinator.api.set_session_timer, value)
        await self.coordinator.async_refresh()
