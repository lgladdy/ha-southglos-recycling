"""Tests for setup and unload of the integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.southglos_bins.const import DOMAIN


async def test_setup_and_unload(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """The entry sets up and unloads cleanly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        title="1 Test Road",
        data={"uprn": "12345", "postcode": "BS1 1AA"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
