"""Sensor platform for South Gloucestershire Bins integration."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, COLLECTION_TYPES
from .coordinator import SouthGlosBinsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: SouthGlosBinsCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Create collection date sensors for each available collection type
    for collection_type in COLLECTION_TYPES:
        if coordinator.is_collection_available(collection_type):
            entities.append(CollectionDateSensor(coordinator, collection_type))
            entities.append(LiveStatusSensor(coordinator, collection_type))
    
    async_add_entities(entities)


class CollectionDateSensor(CoordinatorEntity[SouthGlosBinsCoordinator], SensorEntity):
    """Sensor for collection dates."""

    def __init__(
        self,
        coordinator: SouthGlosBinsCoordinator,
        collection_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._collection_type = collection_type
        self._attr_name = f"Next {collection_type.title()} Collection"
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Return icon for collection type."""
        icons = {
            "refuse": "mdi:delete",
            "recycling": "mdi:recycle", 
            "food": "mdi:food-apple",
            "garden": "mdi:tree"
        }
        return icons.get(self._collection_type, "mdi:calendar")

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        # Check if we need to refresh due to midnight crossing before returning value
        self.hass.async_create_task(self.coordinator.async_request_refresh_if_needed())
        return self.coordinator.get_collection_date(self._collection_type)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        
        # Add days until next collection
        next_collection = self.coordinator.get_collection_date(self._collection_type)
        if next_collection:
            today = date.today()
            days_until = (next_collection - today).days
            attrs["days_until_collection"] = days_until
            
            # Add helpful status
            if days_until == 0:
                attrs["status"] = "Today"
            elif days_until == 1:
                attrs["status"] = "Tomorrow"
            elif days_until < 7:
                attrs["status"] = f"In {days_until} days"
            else:
                attrs["status"] = f"In {days_until} days"
        
        # Check if it's collection day
        attrs["is_collection_day"] = self.coordinator.is_collection_day(self._collection_type)
        
        return attrs


class LiveStatusSensor(CoordinatorEntity[SouthGlosBinsCoordinator], SensorEntity):
    """Sensor for live collection status (only available on collection days)."""

    def __init__(
        self,
        coordinator: SouthGlosBinsCoordinator,
        collection_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._collection_type = collection_type
        self._attr_name = f"{collection_type.title()} Collection Status"
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_status"
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Return icon based on collection status."""
        status = self.coordinator.get_live_status(self._collection_type)
        if not status:
            return "mdi:calendar-clock"
            
        status_lower = status.lower()
        status_icons = {
            "in progress": "mdi:truck",
            "closed completed": "mdi:check-circle",
            "completed": "mdi:check-circle",
            "delayed": "mdi:clock-alert",
            "cancelled": "mdi:cancel",
            "not started": "mdi:clock-outline"
        }
        return status_icons.get(status_lower, "mdi:help-circle")

    @property
    def native_value(self) -> str:
        """Return the live status."""
        # Check if we need to refresh due to midnight crossing before returning value
        self.hass.async_create_task(self.coordinator.async_request_refresh_if_needed())
        live_status = self.coordinator.get_live_status(self._collection_type)
        if live_status:
            return live_status
        
        return "No Status Available"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available 
            and self.coordinator.is_collection_available(self._collection_type)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        
        attrs["is_collection_day"] = self.coordinator.is_collection_day(self._collection_type)
        attrs["collection_type"] = self._collection_type
        
        # Add status reason if available
        reason = self.coordinator.get_live_status_reason(self._collection_type)
        if reason:
            attrs["reason"] = reason
        
        # Add collection schedule info
        if self.coordinator.data:
            collections = self.coordinator.data.get("collections", {})
            collection_info = collections.get(self._collection_type, {})
            
            attrs["schedule"] = collection_info.get("schedule", "")
            attrs["round"] = collection_info.get("round", "")
            attrs["round_group"] = collection_info.get("round_group", "")
            attrs["original_next_collection"] = collection_info.get("original_next_collection")
            attrs["last_updated"] = self.coordinator.data.get("last_updated")
            
            # Add completion time if available
            completed_time = self.coordinator.get_collection_completed_time(self._collection_type)
            if completed_time:
                attrs["completed_time"] = completed_time
        
        return attrs