"""Sensor platform for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import MAX_LENGTH_STATE_STATE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SouthGlosBinsConfigEntry, SouthGlosBinsCoordinator
from .entity import SouthGlosBinsEntity, async_add_collection_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SouthGlosBinsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_collection_entities(
        entry,
        async_add_entities,
        lambda coordinator, collection_type: (
            CollectionDateSensor(coordinator, collection_type),
            LiveStatusSensor(coordinator, collection_type),
        ),
    )


STATUS_ICONS = {
    "in progress": "mdi:truck",
    "closed completed": "mdi:check-circle",
    "completed": "mdi:check-circle",
    "delayed": "mdi:clock-alert",
    "cancelled": "mdi:cancel",
    "not started": "mdi:clock-outline",
}


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

        next_collection = self.coordinator.get_collection_date(self._collection_type)
        if next_collection:
            days_until = (next_collection - dt_util.now().date()).days
            attrs["days_until_collection"] = days_until
            if days_until < 0:
                # Only happens when the council data is stale.
                attrs["status"] = "Past"
            elif days_until == 0:
                attrs["status"] = "Today"
            elif days_until == 1:
                attrs["status"] = "Tomorrow"
            else:
                attrs["status"] = f"In {days_until} days"

        return attrs


class LiveStatusSensor(SouthGlosBinsEntity, SensorEntity):
    """Sensor reporting the live collection status for a collection type."""

    # These change on every poll; keep them out of the recorder.
    _unrecorded_attributes = frozenset({"last_updated", "original_next_collection"})

    def __init__(
        self, coordinator: SouthGlosBinsCoordinator, collection_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, collection_type)
        self._attr_unique_id = f"{coordinator.uprn}_{collection_type}_status"
        self._attr_translation_key = f"{collection_type}_status"

    @property
    def icon(self) -> str | None:
        """Return an icon reflecting the current status.

        The council's status strings are free text, so they can't be mapped in
        icons.json; fall back to the translated default icon when unknown.
        """
        status = self.coordinator.get_live_status(self._collection_type)
        if not status:
            return None
        return STATUS_ICONS.get(status.lower())

    @property
    def native_value(self) -> str | None:
        """Return the live status."""
        status = self.coordinator.get_live_status(self._collection_type)
        # HA rejects states over 255 characters; the API's text is free-form.
        return status[:MAX_LENGTH_STATE_STATE] if status else status

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
                self.coordinator.get_collection_completed_time(self._collection_type)
            )
            if completed_time:
                attrs["completed_time"] = completed_time

        return attrs
