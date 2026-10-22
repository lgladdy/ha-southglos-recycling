"""Diagnostics for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_POSTCODE, CONF_UPRN
from .coordinator import SouthGlosBinsConfigEntry

TO_REDACT = {CONF_UPRN, CONF_POSTCODE, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SouthGlosBinsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "data": coordinator.data,
    }
