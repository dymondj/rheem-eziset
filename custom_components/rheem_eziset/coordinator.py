"""DataUpdateCoordinator for rheem_eziset."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RheemEziSETApi
from .const import DOMAIN, LOGGER, MAX_UPDATE_FAILS

class RheemEziSETDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching data from the API."""

    config_entry: RheemEziSETConfigEntry

    def __init__(self, hass: HomeAssistant, entry: RheemEziSETConfigEntry, api: RheemEziSETApi, update_interval: int) -> None:
        """Initialize."""
        self.api = api
        self.consecutive_fails = 0

        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    @property
    def problem_flag(self) -> bool:
        """Return True if enough successive updates have failed to treat the device as disconnected."""
        return self.consecutive_fails >= MAX_UPDATE_FAILS

    async def _async_update_data(self) -> dict:
        """Update basic data via client."""
        try:
            result = await self.hass.async_add_executor_job(self.api.get_data)
        except Exception as exception:
            # Powerline comms are noisy so the odd failed request is expected.
            self.consecutive_fails += 1
            if self.consecutive_fails == MAX_UPDATE_FAILS:
                # Entities are only told about the first failed update, so tell them that they are now unavailable.
                self.hass.loop.call_soon(self.async_update_listeners)
            raise UpdateFailed(str(exception)) from exception
        self.consecutive_fails = 0
        LOGGER.debug("%s - Final getInfo_data result: %s", DOMAIN, result)
        return result


RheemEziSETConfigEntry = ConfigEntry[RheemEziSETDataUpdateCoordinator]
