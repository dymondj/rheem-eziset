"""Binary Sensor platform for rheem_eziset."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODE_APP_ERROR, MODE_HEATER_ERROR
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator
from .entity import RheemEziSETEntity

BINARY_SENSOR_MAP = [
    # ("description", "key", "icon", "device_class", "entity_category"),
    ("Heater error", "appErrCode", None, BinarySensorDeviceClass.PROBLEM, EntityCategory.DIAGNOSTIC),  # pylint: disable=line-too-long
]


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add binary sensors for passed config_entry in HA."""
    coordinator = entry.runtime_data

    binary_sensors: list[BinarySensorEntity] = [
        RheemEziSETBinarySensor(coordinator, entry, description, key, icon, device_class, entity_category) for description, key, icon, device_class, entity_category in BINARY_SENSOR_MAP
    ]
    binary_sensors.append(RheemEziSETProblemBinarySensor(coordinator, entry))

    async_add_entities(binary_sensors)


class RheemEziSETBinarySensor(RheemEziSETEntity, BinarySensorEntity):
    """rheem_eziset Binary Sensor class."""

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
        description: str,
        key: str,
        icon: str | None,
        device_class: BinarySensorDeviceClass,
        entity_category: EntityCategory,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.description = description
        self.key = key
        self._attr_name = description
        self._attr_unique_id = f"{entry.entry_id}-{description}"
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        data = self.coordinator.data
        if self.key == "appErrCode":
            try:
                return int(data.get(self.key, 0)) != 0 or data.get("mode") in (MODE_HEATER_ERROR, MODE_APP_ERROR)
            except (TypeError, ValueError):
                return None
        return False


class RheemEziSETProblemBinarySensor(RheemEziSETEntity, BinarySensorEntity):
    """rheem_eziset connectivity Binary Sensor class. On means that the device is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Connectivity Problem"

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.description = "Connectivity Problem"
        self._attr_unique_id = f"{entry.entry_id}-connectivity-problem"

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return not self.coordinator.problem_flag

    @property
    def available(self) -> bool:
        """Override availability, this one should always be available."""
        return True
