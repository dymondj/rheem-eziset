"""Button platform for rheem_eziset."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ICON_ALERT
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator
from .entity import RheemEziSETEntity


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add buttons for passed config_entry in HA."""
    async_add_entities([RheemEziSETClearErrorButton(entry.runtime_data, entry)])


class RheemEziSETClearErrorButton(RheemEziSETEntity, ButtonEntity):
    """Clears a bath fill error in the same way as acknowledging the warning in the official app."""

    _attr_name = "Clear bath fill error"
    _attr_icon = ICON_ALERT
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}-clear-bath-fill-error"

    async def async_press(self) -> None:
        """Clear the error."""
        await self.hass.async_add_executor_job(self.coordinator.api.clear_bath_fill_error)
        await self.coordinator.async_refresh()
