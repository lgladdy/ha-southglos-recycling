"""DataUpdateCoordinator for South Gloucestershire Bins."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, time
from typing import Any
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_interval

from .api import SouthGlosBinsAPI, SouthGlosBinsAPIError
from .const import (
    DOMAIN,
    CONF_UPRN,
    UPDATE_INTERVAL_NORMAL,
    UPDATE_INTERVAL_COLLECTION_DAY,
)

_LOGGER = logging.getLogger(__name__)


class SouthGlosBinsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching South Gloucestershire Bins data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.api = SouthGlosBinsAPI(hass)
        self.uprn = entry.data[CONF_UPRN]
        self._last_update_date = None
        self._midnight_check_task = None
        
        # Start with normal update interval
        update_interval = timedelta(seconds=UPDATE_INTERVAL_NORMAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        
        # Schedule midnight checks
        self._schedule_midnight_checks()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Check if we need to force update due to midnight crossing
            current_date = date.today()
            should_force_update = self._should_force_update_on_midnight_crossing(current_date)

            if should_force_update:
                _LOGGER.info("Forcing update due to midnight crossing into collection day")

            _LOGGER.debug(f"Fetching collection data for UPRN {self.uprn} on {current_date}")
            data = await self.api.get_collection_data(self.uprn)

            # Update the last update datetime
            self._last_update_date = datetime.now()
            _LOGGER.debug(f"Updated last_update_date to {self._last_update_date}")
            
            # Check if today is a collection day and adjust update frequency
            await self._adjust_update_interval(data)
            
            return data
            
        except SouthGlosBinsAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _adjust_update_interval(self, data: dict[str, Any]) -> None:
        """Adjust update interval based on whether today is a collection day."""
        today = date.today()
        is_collection_day = False
        
        collections = data.get("collections", {})
        for collection_type, collection_info in collections.items():
            next_collection = collection_info.get("next_collection")
            if next_collection and next_collection == today:
                is_collection_day = True
                break
        
        # Set update interval based on collection day status
        if is_collection_day:
            new_interval = timedelta(seconds=UPDATE_INTERVAL_COLLECTION_DAY)
            _LOGGER.debug("Collection day detected, updating every 15 minutes")
        else:
            new_interval = timedelta(seconds=UPDATE_INTERVAL_NORMAL)
            _LOGGER.debug("Normal day, updating every 24 hours")
        
        # Only update if interval has changed
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            # Schedule next update with new interval
            self._schedule_refresh()

    def _is_collection_day_for_type(self, collection_type: str, collections: dict, live_status: dict, today: date) -> bool:
        """Helper to check if today is collection day for a specific type."""
        collection_info = collections.get(collection_type, {})
        next_collection = collection_info.get("next_collection")
        last_collection = collection_info.get("last_collection")
        
        # Collection day if:
        # 1. Next collection is today, OR
        # 2. Last collection is today AND there's live status (collection in progress/completed today)
        return (next_collection == today or 
                (last_collection == today and collection_type in live_status))

    def is_collection_day(self, collection_type: str | None = None) -> bool:
        """Check if today is a collection day."""
        if not self.data:
            return False
            
        today = date.today()
        collections = self.data.get("collections", {})
        live_status = self.data.get("live_status", {})
        
        if collection_type:
            return self._is_collection_day_for_type(collection_type, collections, live_status, today)
        else:
            # Check if any collection is today
            return any(
                self._is_collection_day_for_type(collection_type_key, collections, live_status, today)
                for collection_type_key in collections.keys()
            )

    def _should_force_update_on_midnight_crossing(self, current_date: date) -> bool:
        """Check if we should force an update due to crossing midnight into a collection day."""
        if not self.data or self._last_update_date is None:
            _LOGGER.debug("No previous data or last update date, not forcing update")
            return False

        # If we haven't crossed to a new day, no need to update
        if self._last_update_date.date() >= current_date:
            _LOGGER.debug(f"Last update was {self._last_update_date}, current date {current_date}, not forcing update")
            return False

        _LOGGER.debug(f"Crossed to new day: last update {self._last_update_date.date()}, current {current_date}")

        # We've moved to a new day - check if today is a collection day for any collection type
        collections = self.data.get("collections", {})
        for collection_type, collection_info in collections.items():
            next_collection = collection_info.get("next_collection")
            if next_collection and next_collection == current_date:
                _LOGGER.debug(f"Today ({current_date}) is collection day for {collection_type}, forcing update")
                return True

        _LOGGER.debug(f"Today ({current_date}) is not a collection day, no forced update needed")
        return False
    
    def _schedule_midnight_checks(self) -> None:
        """Schedule checks to catch collection day transitions when dates change."""
        # Cancel existing task if any
        if self._midnight_check_task:
            self._midnight_check_task()

        # Schedule a task to run every 5 minutes to check for date changes
        # This will catch the transition when we move into a collection day
        self._midnight_check_task = async_track_time_interval(
            self.hass,
            self._check_midnight_crossing,
            timedelta(minutes=5)
        )
    
    async def _check_midnight_crossing(self, now: datetime) -> None:
        """Check if we've crossed midnight and need to update for collection day logic."""
        current_date = now.date()

        # Check if we need to update due to date change
        # We'll check this more frequently instead of just around midnight
        if self._should_force_update_on_midnight_crossing(current_date):
            _LOGGER.info(f"Date crossing detected at {now.strftime('%H:%M')}, forcing update for collection day logic")
            await self.async_request_refresh()

    async def async_request_refresh_if_needed(self) -> None:
        """Request refresh if we've crossed midnight into a collection day."""
        current_date = date.today()
        if self._should_force_update_on_midnight_crossing(current_date):
            _LOGGER.debug("Requesting refresh due to midnight crossing")
            await self.async_request_refresh()

    def get_collection_date(self, collection_type: str) -> date | None:
        """Get next collection date for a specific type."""
        if not self.data:
            return None
            
        collections = self.data.get("collections", {})
        collection_info = collections.get(collection_type, {})
        return collection_info.get("next_collection")

    def get_live_status(self, collection_type: str) -> str | None:
        """Get live status for a collection type."""
        if not self.data:
            return None
            
        live_status = self.data.get("live_status", {})
        status_info = live_status.get(collection_type, {})
        
        if isinstance(status_info, dict):
            return status_info.get("status")
        
        return status_info

    def get_live_status_reason(self, collection_type: str) -> str | None:
        """Get live status reason for a collection type."""
        if not self.data:
            return None
            
        live_status = self.data.get("live_status", {})
        status_info = live_status.get(collection_type, {})
        
        if isinstance(status_info, dict):
            return status_info.get("reason")
        
        return None

    def get_collection_completed_time(self, collection_type: str) -> datetime | None:
        """Get the completion time for a collection type."""
        if not self.data:
            return None
            
        collections = self.data.get("collections", {})
        collection_info = collections.get(collection_type, {})
        return collection_info.get("last_completed")

    def is_collection_available(self, collection_type: str) -> bool:
        """Check if a collection type is available for this address."""
        if not self.data:
            return False
            
        collections = self.data.get("collections", {})
        collection_info = collections.get(collection_type, {})
        return collection_info.get("available", False)
    
    async def async_shutdown(self) -> None:
        """Clean up resources."""
        if self._midnight_check_task:
            self._midnight_check_task()
            self._midnight_check_task = None