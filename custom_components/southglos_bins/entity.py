"""Base entity for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLLECTION_TYPES, DOMAIN, MANUFACTURER
from .coordinator import SouthGlosBinsConfigEntry, SouthGlosBinsCoordinator


@callback
def async_add_collection_entities(
    entry: SouthGlosBinsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[SouthGlosBinsCoordinator, str], Iterable[Entity]],
) -> None:
    """Add entities per collection type, including types that appear later.

    A garden waste subscription can start after the integration is set up, so
    re-check on every coordinator update instead of only at setup time.
    """
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new_types = [
            collection_type
            for collection_type in COLLECTION_TYPES
            if collection_type not in known
            and coordinator.is_collection_available(collection_type)
        ]
        if not new_types:
            return
        known.update(new_types)
        async_add_entities(
            entity
            for collection_type in new_types
            for entity in factory(coordinator, collection_type)
        )

    _async_add_new()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))


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
