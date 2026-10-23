"""Tests for diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.southglos_bins.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacted(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The UPRN, postcode and address are redacted."""
    # Called directly: the HTTP helper's access log breaks under freezegun.
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    entry = diagnostics["entry"]
    assert entry["data"] == {"uprn": "**REDACTED**", "postcode": "**REDACTED**"}
    assert entry["title"] == "**REDACTED**"
    assert entry["unique_id"] == "**REDACTED**"
    assert diagnostics["last_update_success"] is True
    assert set(diagnostics["data"]["collections"]) == {
        "refuse",
        "recycling",
        "garden",
    }
    assert "12345" not in str(diagnostics)
