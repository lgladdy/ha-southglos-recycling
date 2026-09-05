"""Tests for the South Gloucestershire Recycling Collections config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.southglos_bins.api import SouthGlosBinsAPIError
from custom_components.southglos_bins.const import DOMAIN


async def test_single_address_creates_entry(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """A postcode resolving to one address creates an entry directly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "bs1 1aa"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "12345"
    assert result["data"] == {"uprn": "12345", "postcode": "BS1 1AA"}


async def test_multiple_addresses_shows_select_step(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """A postcode with multiple addresses prompts for a selection."""
    mock_api.get_addresses_for_postcode.return_value = [
        {"uprn": "1", "address": "1 Test Road"},
        {"uprn": "2", "address": "2 Test Road"},
    ]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_address"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"uprn": "2"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["uprn"] == "2"


async def test_cannot_connect(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """An API error surfaces the cannot_connect error."""
    mock_api.get_addresses_for_postcode.side_effect = SouthGlosBinsAPIError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_no_addresses(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """An empty address list surfaces the no_addresses_found error."""
    mock_api.get_addresses_for_postcode.return_value = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["errors"] == {"base": "no_addresses_found"}


async def test_duplicate_aborts(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """Configuring the same UPRN twice aborts."""
    MockConfigEntry(domain=DOMAIN, unique_id="12345").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
