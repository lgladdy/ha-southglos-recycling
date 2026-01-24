"""Calendar platform for South Gloucestershire Bins integration."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """Set up calendar platform."""
    coordinator: SouthGlosBinsCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Create one calendar per collection type (only for available types)
    for collection_type in COLLECTION_TYPES:
        if coordinator.is_collection_available(collection_type):
            entities.append(CollectionCalendar(coordinator, collection_type))

    async_add_entities(entities)


class CollectionCalendar(CoordinatorEntity[SouthGlosBinsCoordinator], CalendarEntity):
    """Calendar entity for a collection type."""

    def __init__(
        self,
        coordinator: SouthGlosBinsCoordinator,
        collection_type: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._collection_type = collection_type
        self._attr_name = f"{collection_type.title()} Collection Calendar"
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_calendar"
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
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self.coordinator.data:
            return None

        # Get next collection date
        next_collection = self.coordinator.get_collection_date(self._collection_type)
        if not next_collection:
            return None

        today = date.today()

        # If next collection is today or in the future, create event
        if next_collection >= today:
            is_today = (next_collection == today)
            return self._create_event(next_collection, is_today=is_today)

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        events = []
        today = date.today()

        # Get next collection date
        next_collection = self.coordinator.get_collection_date(self._collection_type)
        if next_collection and start_date.date() <= next_collection <= end_date.date():
            is_today = (next_collection == today)
            events.append(self._create_event(next_collection, is_today=is_today))

        # Optionally: Get last collection date for historical view
        collections = self.coordinator.data.get("collections", {})
        collection_info = collections.get(self._collection_type, {})
        last_collection = collection_info.get("last_collection")

        if last_collection and start_date.date() <= last_collection <= end_date.date():
            # Only add if it's not the same as next collection (avoid duplicates)
            if last_collection != next_collection:
                events.append(self._create_event(last_collection, is_today=False))

        # Sort by date
        events.sort(key=lambda e: e.start)

        return events

    def _create_event(
        self,
        event_date: date,
        is_today: bool = False,
    ) -> CalendarEvent:
        """Create a CalendarEvent for a collection date."""
        # Get collection info from coordinator
        collection_info = {}
        if self.coordinator.data:
            collections = self.coordinator.data.get("collections", {})
            collection_info = collections.get(self._collection_type, {})

        # Build description
        description_parts = []

        # Add schedule
        schedule = collection_info.get("schedule", "")
        if schedule:
            description_parts.append(f"Schedule: {schedule}")

        # Add round information
        round_info = collection_info.get("round", "")
        if round_info:
            description_parts.append(f"Round: {round_info}")

        round_group = collection_info.get("round_group", "")
        if round_group:
            description_parts.append(f"Round Group: {round_group}")

        # Add live status if this is today and collection is active
        if is_today and self.coordinator.is_collection_day(self._collection_type):
            live_status = self.coordinator.get_live_status(self._collection_type)
            if live_status:
                description_parts.append(f"Status: {live_status}")

            reason = self.coordinator.get_live_status_reason(self._collection_type)
            if reason:
                description_parts.append(f"Reason: {reason}")

            # Add completion time if available
            completed_time = self.coordinator.get_collection_completed_time(self._collection_type)
            if completed_time:
                description_parts.append(f"Completed: {completed_time.strftime('%H:%M')}")

        description = "\n".join(description_parts) if description_parts else None

        # Create event (all-day event)
        return CalendarEvent(
            start=event_date,
            end=event_date + timedelta(days=1),
            summary=f"{self._collection_type.title()} Collection",
            description=description,
            location=collection_info.get("round"),
        )
