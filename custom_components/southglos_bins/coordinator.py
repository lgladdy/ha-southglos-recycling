"""DataUpdateCoordinator for South Gloucestershire Bins."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
        
        # Start with normal update interval
        update_interval = timedelta(seconds=UPDATE_INTERVAL_NORMAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.api.get_collection_data(self.uprn)
            
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

    def is_collection_day(self, collection_type: str | None = None) -> bool:
        """Check if today is a collection day."""
        if not self.data:
            return False
            
        today = date.today()
        collections = self.data.get("collections", {})
        live_status = self.data.get("live_status", {})
        
        if collection_type:
            collection_info = collections.get(collection_type, {})
            next_collection = collection_info.get("next_collection")
            last_collection = collection_info.get("last_collection")
            
            # Collection day if:
            # 1. Next collection is today, OR
            # 2. Last collection is today AND there's live status (collection in progress/completed today)
            if next_collection == today:
                return True
            elif last_collection == today and collection_type in live_status:
                return True
            
            return False
        else:
            # Check if any collection is today
            for collection_type_key, collection_info in collections.items():
                next_collection = collection_info.get("next_collection")
                last_collection = collection_info.get("last_collection")
                
                if next_collection == today:
                    return True
                elif last_collection == today and collection_type_key in live_status:
                    return True
        
        return False

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