"""Constants for Rheem EziSET."""
from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

# Component Data
NAME = "Rheem EziSET Water Heater"
IDPREFIX = "rheem_water_heater_"
DOMAIN = "rheem_eziset"
MANUFACTURER = "Rheem"
VERSION = "2026.11.0"
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.WATER_HEATER,
]

# SCAN INTERVAL
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 5  # seconds

# Request handling
# The device refuses connections (and can lock up until it is power cycled) if it receives requests too quickly.
# All requests are therefore serialised and spaced at least this far apart.
MIN_REQUEST_INTERVAL = 0.25  # seconds
REQUEST_TIMEOUT = 6.1  # seconds
# Data which rarely changes (firmware version, limits) is only refreshed this often.
STATIC_REFRESH_INTERVAL = 3600  # seconds
# Number of successive failed updates before the device is treated as unavailable.
MAX_UPDATE_FAILS = 5

# Discovery (UDP broadcast used by the official app)
DISCOVERY_PORT = 2015
DISCOVERY_MESSAGE = b"Rheem_CFGH"
DISCOVERY_TIMEOUT = 1.5  # seconds

# Modes
MODE_INIT = 0
MODE_IDLE = 5
MODE_HEATING_CONTROL = 10
MODE_HEATING = 15
MODE_HEATING_PAUSED = 20
MODE_BATHFILL_CONTROL = 25
MODE_BATHFILLING = 30
MODE_BATHFILL_FINISHED = 35
MODE_HEATER_ERROR = 90
MODE_APP_ERROR = 99

# Mode Dictionary (names taken from the official app)
CONST_MODE_MAP = {
    MODE_INIT: ("Initialising", "mdi:water-boiler-auto"),
    MODE_IDLE: ("Idle", "mdi:water-boiler-auto"),
    MODE_HEATING_CONTROL: ("Heating Control Mode", "mdi:thermometer"),
    MODE_HEATING: ("Heating (Conventional Mode)", "mdi:fire"),
    MODE_HEATING_PAUSED: ("Heating Paused", "mdi:pause-circle-outline"),
    MODE_BATHFILL_CONTROL: ("Bath Fill Control Mode", "mdi:bathtub-outline"),
    MODE_BATHFILLING: ("Heating (Bath Fill Mode)", "mdi:bathtub"),
    MODE_BATHFILL_FINISHED: ("Idle (Bath Fill Mode Complete)", "mdi:water-boiler-off"),
    MODE_HEATER_ERROR: ("Heater Error", "mdi:water-boiler-alert"),
    MODE_APP_ERROR: ("Application Error", "mdi:alert-circle-outline"),
}

# Status
STATE_OFF = 0
STATE_IDLE = 1
STATE_BURNING = 2
STATE_WATER_STOP = 3

# Status Dictionary
CONST_STATUS_MAP = {
    STATE_OFF: ("Off", "mdi:water-boiler-off"),
    STATE_IDLE: ("Idle", "mdi:water-boiler-auto"),
    STATE_BURNING: ("Heating", "mdi:water-boiler"),
    STATE_WATER_STOP: ("Bath Fill Complete (Off)", "mdi:water-boiler-off"),
}

# appErrCode is a bit field. Descriptions are taken from the official app.
APP_ERROR_FLAGS = {
    1: "Bath fill did not start properly",
    2: "Bath fill did not finish properly",
    4: "Water flow detected at power up",
    8: "Bath fill response timeout (taps not closed)",
    16: "Communication timeout between control module and heater",
    32: "Water flow detected after bath fill cancelled",
    64: "Water flow detected after bath fill (taps not closed)",
    128: "No first used date set",
}

# Limits used by the official app
HEATER_NAME_MAX_LENGTH = 10
SESSION_TIMER_MIN = 60  # seconds
SESSION_TIMER_MAX = 900  # seconds

# Services
SERVICE_START_BATH_FILL = "start_bath_fill"
SERVICE_CANCEL_BATH_FILL = "cancel_bath_fill"
SERVICE_SET_HEATER_NAME = "set_heater_name"
SERVICE_SYNC_TIME = "sync_time"
ATTR_VOLUME = "volume"

# Icon Dictionary
ICON_ALERT = "mdi:alert-circle-outline"
ICON_BATH = "mdi:bathtub"
ICON_NAME = "mdi:label"
ICON_RAW = "mdi:raw"
ICON_TAPON = "mdi:water-pump"
ICON_TAPOFF = "mdi:water-pump-off"
ICON_TEMP = "mdi:thermometer"
ICON_TIMER = "mdi:timer"
ICON_WATERHEATER = "mdi:water-boiler"
