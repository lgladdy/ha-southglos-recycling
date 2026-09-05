"""Base entity for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SouthGlosBinsCoordinator


class SouthGlosBinsEntity(CoordinatorEntity[SouthGlosBinsCoordinator]):
    """Common base for South Gloucestershire Bins entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SouthGlosBinsCoordinator, collection_type: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._collection_type = collection_type
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.uprn)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model="Waste collection",
            name=coordinator.config_entry.title,
            configuration_url="https://www.southglos.gov.uk/bins-waste-and-recycling/",
        )

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self.coordinator.is_collection_available(
            self._collection_type
        )
