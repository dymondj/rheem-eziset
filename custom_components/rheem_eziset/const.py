"""Constants for Rheem EziSET."""
from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

# Component Data
NAME = "Rheem EziSET Water Heater"
DOMAIN = "rheem_eziset"
MANUFACTURER = "Rheem"
VERSION = "2023.12.0"
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
#    Platform.BINARY_SENSOR,
#    Platform.NUMBER,
#    Platform.WATER_HEATER,
]

# SCAN INTERVAL
CONF_SYNC_INTERVAL = "sync_interval"
DEFAULT_SYNC_INTERVAL = 30 # seconds

# Mode Dictionary
CONST_MODE_MAP = {
    5:  ("Idle",                                    "mdi:water-boiler-auto"),
    10: ("Heating Control Mode",                    "mdi:thermometer"),
    15: ("Heating (Conventional Mode)",             "mdi:fire"),
    20: ("Idle (Bath Fill Mode Waiting for Tap)",   "mdi:bathtub-outline"),
    25: ("Heating (Bath Fill Mode)",                "mdi:bathtub"),
    35: ("Idle (Bath Fill Mode Complete)",          "mdi:water-boiler-off"),
}

# Status Dictionary
CONST_STATUS_MAP = {
    1:  ("Idle",                        "mdi:water-boiler-auto"),
    2:  ("Heating",                     "mdi:water-boiler"),
    3:  ("Bath Fill Complete (Off)",    "mdi:water-boiler-off"),
}

# Icon Dictionary
ICON_TAPON = "mdi:water-pump"
ICON_TAPOFF = "mdi:water-pump-off"
ICON_WATERHEATER = "mdi:water-boiler"

