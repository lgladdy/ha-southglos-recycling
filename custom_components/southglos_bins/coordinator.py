"""DataUpdateCoordinator for South Gloucestershire Bins."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SouthGlosBinsAPI, SouthGlosBinsAPIError
from .const import (
    CONF_POSTCODE,
    CONF_UPRN,
    DOMAIN,
    UPDATE_INTERVAL_COLLECTION_DAY,
    UPDATE_INTERVAL_NORMAL,
)

_LOGGER = logging.getLogger(__name__)

type SouthGlosBinsConfigEntry = ConfigEntry[SouthGlosBinsCoordinator]


class SouthGlosBinsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage fetching South Gloucestershire Bins data."""

    config_entry: SouthGlosBinsConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SouthGlosBinsConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_NORMAL),
            config_entry=entry,
        )
        self.api = SouthGlosBinsAPI(hass)
        self.uprn: str = entry.data[CONF_UPRN]
        self.postcode: str = entry.data.get(CONF_POSTCODE, "")

        # Collection-day detection is derived from the current date, so force a
        # refresh just after midnight to recalculate state and attributes.
        entry.async_on_unload(
            async_track_time_change(
                hass, self._handle_midnight, hour=0, minute=0, second=30
            )
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            data = await self.api.get_collection_data(self.uprn)
        except SouthGlosBinsAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        self._adjust_update_interval(data)
        return data

    async def _handle_midnight(self, now: datetime) -> None:
        """Refresh shortly after midnight so date-based state stays correct."""
        _LOGGER.debug("Midnight rollover detected, refreshing collection data")
        await self.async_request_refresh()

    @callback
    def _adjust_update_interval(self, data: dict[str, Any]) -> None:
        """Poll more frequently on collection days for live status updates."""
        today = dt_util.now().date()
        is_collection_day = any(
            info.get("next_collection") == today
            for info in data.get("collections", {}).values()
        )
        new_interval = timedelta(
            seconds=UPDATE_INTERVAL_COLLECTION_DAY
            if is_collection_day
            else UPDATE_INTERVAL_NORMAL
        )
        if self.update_interval != new_interval:
            _LOGGER.debug("Adjusting update interval to %s", new_interval)
            self.update_interval = new_interval

    def _is_collection_day_for_type(self, collection_type: str, today: date) -> bool:
        """Return whether today is a collection day for a specific type."""
        collections = self.data.get("collections", {})
        live_status = self.data.get("live_status", {})
        collection_info = collections.get(collection_type, {})
        next_collection = collection_info.get("next_collection")
        last_collection = collection_info.get("last_collection")

        # Collection day when the next collection is today, or the collection
        # happened today and there is live status for it (in progress / done).
        return next_collection == today or (
            last_collection == today and collection_type in live_status
        )

    def is_collection_day(self, collection_type: str | None = None) -> bool:
        """Return whether today is a collection day."""
        if not self.data:
            return False

        today = dt_util.now().date()
        if collection_type:
            return self._is_collection_day_for_type(collection_type, today)

        return any(
            self._is_collection_day_for_type(key, today)
            for key in self.data.get("collections", {})
        )

    def get_collection_date(self, collection_type: str) -> date | None:
        """Return the next collection date for a type."""
        if not self.data:
            return None
        return (
            self.data.get("collections", {})
            .get(collection_type, {})
            .get("next_collection")
        )

    def get_live_status(self, collection_type: str) -> str | None:
        """Return the live status for a collection type."""
        if not self.data:
            return None
        status_info = self.data.get("live_status", {}).get(collection_type, {})
        if isinstance(status_info, dict):
            return status_info.get("status")
        return status_info

    def get_live_status_reason(self, collection_type: str) -> str | None:
        """Return the live status reason for a collection type."""
        if not self.data:
            return None
        status_info = self.data.get("live_status", {}).get(collection_type, {})
        if isinstance(status_info, dict):
            return status_info.get("reason")
        return None

    def get_collection_completed_time(self, collection_type: str) -> datetime | None:
        """Return the completion time for a collection type."""
        if not self.data:
            return None
        return (
            self.data.get("collections", {})
            .get(collection_type, {})
            .get("last_completed")
        )

    def is_collection_available(self, collection_type: str) -> bool:
        """Return whether a collection type is available for this address."""
        if not self.data:
            return False
        return (
            self.data.get("collections", {})
            .get(collection_type, {})
            .get("available", False)
        )
