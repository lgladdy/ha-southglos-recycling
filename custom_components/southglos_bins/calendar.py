"""Calendar platform for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import COLLECTION_ICONS, COLLECTION_TYPES
from .coordinator import SouthGlosBinsConfigEntry, SouthGlosBinsCoordinator
from .entity import SouthGlosBinsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SouthGlosBinsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform."""
    coordinator = entry.runtime_data

    async_add_entities(
        CollectionCalendar(coordinator, collection_type)
        for collection_type in COLLECTION_TYPES
        if coordinator.is_collection_available(collection_type)
    )


class CollectionCalendar(SouthGlosBinsEntity, CalendarEntity):
    """Calendar entity exposing collection dates for a collection type."""

    def __init__(
        self, coordinator: SouthGlosBinsCoordinator, collection_type: str
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, collection_type)
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_calendar"
        self._attr_translation_key = f"{collection_type}_calendar"
        self._attr_icon = COLLECTION_ICONS.get(collection_type, "mdi:calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        next_collection = self.coordinator.get_collection_date(self._collection_type)
        today = dt_util.now().date()
        if not next_collection or next_collection < today:
            return None
        return self._create_event(next_collection, is_today=next_collection == today)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        today = dt_util.now().date()
        events: list[CalendarEvent] = []
        collection_info = self.coordinator.data.get("collections", {}).get(
            self._collection_type, {}
        )

        next_collection = self.coordinator.get_collection_date(self._collection_type)
        if next_collection and start_date.date() <= next_collection <= end_date.date():
            events.append(
                self._create_event(next_collection, is_today=next_collection == today)
            )

        last_collection = collection_info.get("last_collection")
        if (
            last_collection
            and last_collection != next_collection
            and start_date.date() <= last_collection <= end_date.date()
        ):
            events.append(self._create_event(last_collection, is_today=False))

        events.sort(key=lambda event: event.start)
        return events

    def _create_event(self, event_date: date, *, is_today: bool) -> CalendarEvent:
        """Build a CalendarEvent for a collection date."""
        collection_info = {}
        if self.coordinator.data:
            collection_info = self.coordinator.data.get("collections", {}).get(
                self._collection_type, {}
            )

        description_parts: list[str] = []
        if schedule := collection_info.get("schedule"):
            description_parts.append(f"Schedule: {schedule}")
        if round_info := collection_info.get("round"):
            description_parts.append(f"Round: {round_info}")
        if round_group := collection_info.get("round_group"):
            description_parts.append(f"Round Group: {round_group}")

        if is_today and self.coordinator.is_collection_day(self._collection_type):
            if live_status := self.coordinator.get_live_status(self._collection_type):
                description_parts.append(f"Status: {live_status}")
            if reason := self.coordinator.get_live_status_reason(self._collection_type):
                description_parts.append(f"Reason: {reason}")
            completed_time = self.coordinator.get_collection_completed_time(
                self._collection_type
            )
            if completed_time:
                description_parts.append(
                    f"Completed: {completed_time.strftime('%H:%M')}"
                )

        return CalendarEvent(
            start=event_date,
            end=event_date + timedelta(days=1),
            summary=f"{self._collection_type.title()} Collection",
            description="\n".join(description_parts) or None,
            location=collection_info.get("round") or None,
        )
