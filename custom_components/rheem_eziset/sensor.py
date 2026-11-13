"""Sensor platform for rheem_eziset."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    APP_ERROR_FLAGS,
    CONST_MODE_MAP,
    CONST_STATUS_MAP,
    ICON_ALERT,
    ICON_BATH,
    ICON_NAME,
    ICON_RAW,
    ICON_TAPOFF,
    ICON_TAPON,
    ICON_TEMP,
    ICON_TIMER,
    ICON_WATERHEATER,
)
from .coordinator import RheemEziSETConfigEntry, RheemEziSETDataUpdateCoordinator
from .entity import RheemEziSETEntity

TIME_MINUTES = UnitOfTime.MINUTES
TIME_SECONDS = UnitOfTime.SECONDS
VOLUME_LITERS = UnitOfVolume.LITERS
CELSIUS = UnitOfTemperature.CELSIUS

SENSOR_MAP = [
    # ("description",        "key",          "unit",                             "icon",             "device_class",                         "state_class",                      "entity_category",              "enabled_default"), # pylint: disable=line-too-long
    ("Flow", "flow", f"{VOLUME_LITERS}/{TIME_MINUTES}", ICON_TAPON, None, SensorStateClass.MEASUREMENT, None, True),  # pylint: disable=line-too-long
    ("Status", "state", None, ICON_WATERHEATER, None, None, None, True),  # pylint: disable=line-too-long
    ("Mode", "mode", None, ICON_WATERHEATER, None, None, None, True),  # pylint: disable=line-too-long
    ("Status raw", "state", None, ICON_RAW, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Mode raw", "mode", None, ICON_RAW, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Heater error raw", "appErrCode", None, ICON_RAW, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Heater error description", "appErrCode", None, ICON_ALERT, None, None, EntityCategory.DIAGNOSTIC, True),  # pylint: disable=line-too-long
    ("Heater fault code", "heaterErrCode", None, ICON_ALERT, None, None, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Session timeout", "sTimeout", TIME_SECONDS, ICON_TIMER, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, True),  # pylint: disable=line-too-long
    ("Current Temperature", "temp", CELSIUS, ICON_TEMP, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Bath fill progress", "fillPercent", PERCENTAGE, ICON_BATH, None, SensorStateClass.MEASUREMENT, None, True),  # pylint: disable=line-too-long
    ("Heater Name", "heaterName", None, ICON_NAME, None, None, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Heater Model", "heaterModel", None, ICON_NAME, None, None, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Firmware build", "Build", None, ICON_NAME, None, None, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
    ("Warm boot count", "WarmBootCount", None, ICON_RAW, None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, False),  # pylint: disable=line-too-long
]


async def async_setup_entry(hass: HomeAssistant, entry: RheemEziSETConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator = entry.runtime_data

    sensors = [
        RheemEziSETSensor(coordinator, entry, description, key, unit, icon, device_class, state_class, entity_category, enabled_default)
        for description, key, unit, icon, device_class, state_class, entity_category, enabled_default in SENSOR_MAP  # pylint: disable=line-too-long
    ]

    async_add_entities(sensors)


def describe_app_error(code: int) -> list[str]:
    """Return the description of each flag which is set in appErrCode."""
    return [description for flag, description in APP_ERROR_FLAGS.items() if code & flag]


class RheemEziSETSensor(RheemEziSETEntity, SensorEntity):
    """rheem_eziset Sensor class."""

    def __init__(
        self,
        coordinator: RheemEziSETDataUpdateCoordinator,
        entry: RheemEziSETConfigEntry,
        description: str,
        key: str,
        unit: str | None,
        icon: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        entity_category: EntityCategory | None,
        enabled_default: bool,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.description = description
        self.key = key
        self._icon = icon
        self._attr_name = description
        self._attr_unique_id = f"{entry.entry_id}-{description}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_entity_registry_enabled_default = enabled_default
        if description in ("Flow", "Bath fill progress"):
            self._attr_suggested_display_precision = 1

    def _mapped(self, mapping: dict) -> tuple[str, str] | None:
        """Return the (name, icon) for the raw value of this sensor, or None if there is no value."""
        try:
            result = int(self.coordinator.data.get(self.key))
        except (TypeError, ValueError):
            return None
        return mapping.get(result, (f"Unknown ({result})", self._icon))

    @property
    def native_value(self):
        """Return the native_value of the sensor."""
        result = self.coordinator.data.get(self.key)
        if self.description == "Status":
            mapped = self._mapped(CONST_STATUS_MAP)
            return mapped[0] if mapped else None
        if self.description == "Mode":
            mapped = self._mapped(CONST_MODE_MAP)
            return mapped[0] if mapped else None
        if self.description == "Heater error description":
            try:
                errors = describe_app_error(int(result))
            except (TypeError, ValueError):
                return None
            # States are limited to 255 characters, the full list is in the attributes.
            return ", ".join(errors)[:255] if errors else "No error"
        if self.description == "Heater fault code":
            # The heater only reports a fault code when it has a fault.
            return result if result is not None else 0
        return result

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra information for some sensors."""
        data = self.coordinator.data
        if self.description == "Heater error description":
            try:
                return {"errors": describe_app_error(int(data.get(self.key)))}
            except (TypeError, ValueError):
                return None
        if self.description == "Bath fill progress":
            return {
                "target_temperature": data.get("bathtemp"),
                "target_volume": data.get("bathvol"),
                "controlled_by_home_assistant": self.coordinator.api.bath_fill_active,
            }
        return None

    @property
    def icon(self):
        """Return the icon with processing in the case of some sensors."""
        if self.description == "Flow":
            try:
                if float(self.coordinator.data.get(self.key)) != 0:
                    return ICON_TAPON
            except (TypeError, ValueError):
                pass
            return ICON_TAPOFF
        if self.description == "Status":
            mapped = self._mapped(CONST_STATUS_MAP)
            return mapped[1] if mapped else self._icon
        if self.description == "Mode":
            mapped = self._mapped(CONST_MODE_MAP)
            return mapped[1] if mapped else self._icon
        return self._icon
