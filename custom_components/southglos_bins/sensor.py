"""Sensor platform for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    """Set up the sensor platform."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []
    for collection_type in COLLECTION_TYPES:
        if coordinator.is_collection_available(collection_type):
            entities.append(CollectionDateSensor(coordinator, collection_type))
            entities.append(LiveStatusSensor(coordinator, collection_type))

    async_add_entities(entities)


class CollectionDateSensor(SouthGlosBinsEntity, SensorEntity):
    """Sensor reporting the next collection date for a collection type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self, coordinator: SouthGlosBinsCoordinator, collection_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, collection_type)
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_date"
        self._attr_translation_key = f"{collection_type}_date"
        self._attr_icon = COLLECTION_ICONS.get(collection_type, "mdi:calendar")

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        return self.coordinator.get_collection_date(self._collection_type)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            "is_collection_day": self.coordinator.is_collection_day(
                self._collection_type
            )
        }

        next_collection = self.coordinator.get_collection_date(
            self._collection_type
        )
        if next_collection:
            days_until = (next_collection - dt_util.now().date()).days
            attrs["days_until_collection"] = days_until
            if days_until == 0:
                attrs["status"] = "Today"
            elif days_until == 1:
                attrs["status"] = "Tomorrow"
            else:
                attrs["status"] = f"In {days_until} days"

        return attrs


class LiveStatusSensor(SouthGlosBinsEntity, SensorEntity):
    """Sensor reporting the live collection status for a collection type."""

    def __init__(
        self, coordinator: SouthGlosBinsCoordinator, collection_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, collection_type)
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_status"
        self._attr_translation_key = f"{collection_type}_status"

    @property
    def icon(self) -> str:
        """Return an icon reflecting the current status."""
        status = self.coordinator.get_live_status(self._collection_type)
        if not status:
            return "mdi:calendar-clock"

        return {
            "in progress": "mdi:truck",
            "closed completed": "mdi:check-circle",
            "completed": "mdi:check-circle",
            "delayed": "mdi:clock-alert",
            "cancelled": "mdi:cancel",
            "not started": "mdi:clock-outline",
        }.get(status.lower(), "mdi:help-circle")

    @property
    def native_value(self) -> str | None:
        """Return the live status."""
        return self.coordinator.get_live_status(self._collection_type)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            "collection_type": self._collection_type,
            "is_collection_day": self.coordinator.is_collection_day(
                self._collection_type
            ),
        }

        reason = self.coordinator.get_live_status_reason(self._collection_type)
        if reason:
            attrs["reason"] = reason

        if self.coordinator.data:
            collection_info = self.coordinator.data.get("collections", {}).get(
                self._collection_type, {}
            )
            attrs["schedule"] = collection_info.get("schedule", "")
            attrs["round"] = collection_info.get("round", "")
            attrs["round_group"] = collection_info.get("round_group", "")
            attrs["original_next_collection"] = collection_info.get(
                "original_next_collection"
            )
            attrs["last_updated"] = self.coordinator.data.get("last_updated")

            completed_time: datetime | None = (
                self.coordinator.get_collection_completed_time(
                    self._collection_type
                )
            )
            if completed_time:
                attrs["completed_time"] = completed_time

        return attrs
