"""All API calls belong here."""
from __future__ import annotations

from datetime import datetime
import json
import threading
import time

import requests

from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    HEATER_NAME_MAX_LENGTH,
    LOGGER,
    MIN_REQUEST_INTERVAL,
    MODE_IDLE,
    REQUEST_TIMEOUT,
    SESSION_TIMER_MAX,
    SESSION_TIMER_MIN,
    STATIC_REFRESH_INTERVAL,
)


class RheemEziSETError(HomeAssistantError):
    """A request to the device failed or returned something unexpected."""


class RheemEziSETControlError(RheemEziSETError):
    """Control of the water heater could not be taken."""


class RheemEziSETApi:
    """
    Define the Rheem EziSET API.

    One instance must be shared by everything which talks to a device. The device only copes with one request at a
    time and misbehaves if requests arrive too quickly, so every request goes through a lock and is rate limited.
    """

    def __init__(self, host: str) -> None:
        """Initialise the basic parameters."""
        self.host = host
        self.base_url = f"http://{host}/"
        self._lock = threading.RLock()
        self._session = requests.Session()
        self._last_request: float = 0.0
        self._static: dict = {}
        self._static_time: float = 0.0
        self._pcb_info_supported = True
        self._bath_sid = 0

    @property
    def bath_fill_active(self) -> bool:
        """Return True if this integration currently holds a bath fill session."""
        return self._bath_sid != 0

    # ----------------------------------------------------------------------------------------------------------
    # Low level requests
    # ----------------------------------------------------------------------------------------------------------

    def _get_text(self, page: str) -> str:
        """Get a page from the device, one request at a time and no faster than the device can handle."""
        url = self.base_url + page
        with self._lock:
            wait = MIN_REQUEST_INTERVAL - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            try:
                response = self._session.get(url, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as err:
                raise RheemEziSETError(f"{DOMAIN} - error communicating with {url}: {err}") from err
            finally:
                self._last_request = time.monotonic()

        # The device occasionally pads its responses with NUL characters.
        text = response.text.replace("\x00", "").strip()
        LOGGER.debug("%s - %s response: %s", DOMAIN, page, text)
        return text

    def _get(self, page: str) -> dict:
        """Get a page and convert the JSON response to a dict."""
        text = self._get_text(page)
        try:
            data = json.loads(text)
        except ValueError as err:
            raise RheemEziSETError(f"{DOMAIN} - response for {page} was not valid json. Response was: {text[:200]}") from err
        if not isinstance(data, dict):
            raise RheemEziSETError(f"{DOMAIN} - unexpected response for {page}. Response was: {text[:200]}")
        return data

    # ----------------------------------------------------------------------------------------------------------
    # Reading data
    # ----------------------------------------------------------------------------------------------------------

    def get_data(self) -> dict:
        """Gather sensor data."""
        with self._lock:
            page = f"getInfo.cgi?sid={self._bath_sid}" if self._bath_sid else "getInfo.cgi"
            info = self._get(page)
            if "mode" not in info:
                raise RheemEziSETError(f"{DOMAIN} - unexpected response for {page}: {info}")

            if self._bath_sid and info.get("bathfillCtrl") != 1:
                # The bath fill session has ended (completed, cancelled elsewhere or timed out).
                LOGGER.debug("%s - bath fill session %s has ended", DOMAIN, self._bath_sid)
                self._bath_sid = 0

            if not self._static or time.monotonic() - self._static_time > STATIC_REFRESH_INTERVAL:
                self._refresh_static()

            return {**self._static, **info}

    def _refresh_static(self) -> None:
        """Refresh the data which rarely changes (firmware version, limits and diagnostics)."""
        try:
            static = self._get("version.cgi")
            if "FWversion" not in static:
                raise RheemEziSETError(f"{DOMAIN} - unexpected response for version.cgi: {static}")
            params = self._get("getParams.cgi")
            if "tempMax" not in params:
                raise RheemEziSETError(f"{DOMAIN} - unexpected response for getParams.cgi: {params}")
            static |= params
        except RheemEziSETError:
            if not self._static:
                raise
            # Keep using the previous values and try again on the next update.
            LOGGER.debug("%s - could not refresh static data, keeping previous values", DOMAIN)
            return

        if self._pcb_info_supported:
            try:
                pcb_info = self._get("getPCBInfoBkupReg.cgi")
                # FWversion is already known. TempSetting duplicates temp from getInfo.cgi.
                static |= {key: pcb_info[key] for key in ("Build", "WarmBootCount", "ErrHandlerVal", "BootSignature") if key in pcb_info}
            except RheemEziSETError:
                # Not every firmware version has to support this diagnostic command.
                LOGGER.debug("%s - getPCBInfoBkupReg.cgi is not supported by this device", DOMAIN)
                self._pcb_info_supported = False

        self._static = static
        self._static_time = time.monotonic()

    # ----------------------------------------------------------------------------------------------------------
    # Control
    # ----------------------------------------------------------------------------------------------------------

    def _check_control_issues(self) -> None:
        """Check for any issues with taking control."""
        result = self._get("getInfo.cgi")
        if result.get("sTimeout") != 0:
            raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take control - it appears another user has control. Got this response: {result}")
        if result.get("mode") != MODE_IDLE:
            raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take control - it appears that the water_heater is in use. Got this response: {result}")
        if float(result.get("flow", 0)) != 0:
            raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take control - it appears that the water_heater is in use. Got this response: {result}")

    def _release_heating_control(self, sid: int) -> None:
        """Hand back conventional control."""
        page = f"ctrl.cgi?sid={sid}&heatingCtrl=0"
        try:
            data_response = self._get(page)
        except RheemEziSETError as err:
            LOGGER.error("%s - Couldn't release control with request: %s. Error was: %s", DOMAIN, page, err)
            return
        if data_response.get("sid", 0) != 0:
            LOGGER.error("%s - Couldn't release control with request: %s. Result was: %s", DOMAIN, page, data_response)

    def _set_param(self, param: str, response_param: str | None = None, response_check: int | None = None) -> dict:
        """Take control, set a parameter using set.cgi and then release control."""
        with self._lock:
            if self._bath_sid:
                raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take control - a bath fill started by Home Assistant is in progress.")
            self._check_control_issues()

            # Attempt to take control
            page = "ctrl.cgi?sid=0&heatingCtrl=1"
            data_response = self._get(page)
            sid = data_response.get("sid") or 0
            if data_response.get("heatingCtrl") != 1 or sid == 0:
                # Something wrong happened. Hand back control (if any) and report it.
                if sid != 0:
                    self._release_heating_control(sid)
                raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take control. Result of {page} was: {data_response}")

            try:
                page = f"set.cgi?sid={sid}&{param}"
                data_response = self._get(page)
                if "reason" in data_response:
                    raise RheemEziSETError(f"{DOMAIN} - The device refused {param}: {data_response['reason']}")
                if response_param is not None and data_response.get(response_param) != response_check:
                    raise RheemEziSETError(f"{DOMAIN} - Error when setting {param}. Result was: {data_response}")

                # Per @bajarrr API seems to need a wait. Otherwise the setting doesn't set."
                time.sleep(0.15)
            finally:
                self._release_heating_control(sid)

            return data_response

    def set_temp(self, temp: float | None, min_temp: float, max_temp: float) -> None:
        """Set temperature."""
        if temp is None:
            raise RheemEziSETError(f"{DOMAIN} - No temperature was set. Ignoring call to set temperature.")
        if temp < int(min_temp):
            raise RheemEziSETError(f"{DOMAIN} - An invalid temperature ({temp}) was attempted to be set. This is below the minimum temperature ({min_temp}).")
        if temp > int(max_temp):
            raise RheemEziSETError(f"{DOMAIN} - An invalid temperature ({temp}) was attempted to be set. This is above the maximum temperature ({max_temp}).")

        temp = int(round(temp))
        self._set_param(param=f"setTemp={temp}", response_param="reqtemp", response_check=temp)

    def set_session_timer(self, session_timer: float | None) -> None:
        """Set session timer."""
        if session_timer is None:
            raise RheemEziSETError(f"{DOMAIN} - No session timer was set. Ignoring call to set session timer.")
        if session_timer < SESSION_TIMER_MIN:
            raise RheemEziSETError(f"{DOMAIN} - An invalid session timer ({session_timer}) was attempted to be set. This is below the minimum session timer ({SESSION_TIMER_MIN}).")
        if session_timer > SESSION_TIMER_MAX:
            raise RheemEziSETError(f"{DOMAIN} - An invalid session timer ({session_timer}) was attempted to be set. This is above the maximum session timer ({SESSION_TIMER_MAX}).")

        self._set_param(param=f"setSessionTimer={int(round(session_timer))}")

    def set_heater_name(self, name: str) -> None:
        """Rename the heater. This is the name reported by heaterName.cgi and shown in the official app."""
        name = (name or "").strip()
        if not name.isascii() or not name.isalnum() or len(name) > HEATER_NAME_MAX_LENGTH:
            raise RheemEziSETError(f"{DOMAIN} - An invalid heater name ({name}) was attempted to be set. Names must be 1 to {HEATER_NAME_MAX_LENGTH} letters or numbers.")

        self._set_param(param=f"setHeaterName={name}")

    # ----------------------------------------------------------------------------------------------------------
    # Bath fill
    # ----------------------------------------------------------------------------------------------------------

    def start_bath_fill(self, temp: float, volume: float) -> None:
        """Take bath fill control. The heater then waits for the hot tap to be opened and shuts off at the volume."""
        with self._lock:
            if self._bath_sid:
                raise RheemEziSETControlError(f"{DOMAIN} - A bath fill started by Home Assistant is already in progress.")
            if not self._static:
                self._refresh_static()

            for value, description, key_min, key_max in ((temp, "temperature", "bathtempMin", "bathtempMax"), (volume, "volume", "bathvolMin", "bathvolMax")):
                minimum = self._static.get(key_min)
                maximum = self._static.get(key_max)
                if minimum is None or maximum is None:
                    raise RheemEziSETError(f"{DOMAIN} - The device did not report its bath fill {description} limits.")
                if value < minimum or value > maximum:
                    raise RheemEziSETError(f"{DOMAIN} - An invalid bath fill {description} ({value}) was requested. It must be between {minimum} and {maximum}.")

            self._check_control_issues()

            page = f"ctrl.cgi?sid=0&bathfillCtrl=1&setBathTemp={int(round(temp))}&setBathVol={int(round(volume))}"
            data_response = self._get(page)
            sid = data_response.get("sid") or 0
            if data_response.get("bathfillCtrl") != 1 or sid == 0:
                raise RheemEziSETControlError(f"{DOMAIN} - Couldn't take bath fill control. Result of {page} was: {data_response}")
            self._bath_sid = sid

    def cancel_bath_fill(self) -> None:
        """Cancel (or finish) the bath fill started by Home Assistant and hand back control."""
        with self._lock:
            if not self._bath_sid:
                raise RheemEziSETControlError(f"{DOMAIN} - There is no bath fill started by Home Assistant to cancel.")
            page = f"ctrl.cgi?sid={self._bath_sid}&bathfillCtrl=0"
            data_response = self._get(page)
            if data_response.get("bathfillCtrl", 0) != 0:
                raise RheemEziSETControlError(f"{DOMAIN} - Couldn't release bath fill control. Result of {page} was: {data_response}")
            self._bath_sid = 0

    def clear_bath_fill_error(self) -> None:
        """Clear a bath fill error (appErrCode) in the same way as the official app."""
        self._simple_command("clearAppError.cgi?bathfill=0")

    def sync_time(self, now: datetime) -> None:
        """Send the date and time to the device. The official app does this when appErrCode reports no first used date."""
        self._simple_command("dt.cgi?02=" + now.strftime("%y%m%d%H%M%S"))

    def _simple_command(self, page: str) -> None:
        """Send a command for which the format of the response is not known."""
        text = self._get_text(page)
        if "Invalid command" in text:
            raise RheemEziSETError(f"{DOMAIN} - The device does not support {page.split('?', maxsplit=1)[0]}.")
