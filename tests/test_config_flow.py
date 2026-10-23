"""Tests for the South Gloucestershire Recycling Collections config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
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
    assert result["title"] == "2 Test Road"
    assert result["result"].unique_id == "12345"
    assert result["data"] == {"uprn": "12345", "postcode": "BS1 1AA"}
    mock_api.get_addresses_for_postcode.assert_awaited_once_with("BS1 1AA")


async def test_multiple_addresses_shows_select_step(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """A postcode with multiple addresses prompts for a selection."""
    mock_api.get_addresses_for_postcode.return_value = [
        {"uprn": "1", "address": "1 Test Road, BS1 1AA", "name": "1 Test Road"},
        {"uprn": "2", "address": "2 Test Road, BS1 1AA", "name": "2 Test Road"},
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


async def test_cannot_connect(
    hass: HomeAssistant, mock_api: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """An API error surfaces the cannot_connect error without a traceback."""
    mock_api.get_addresses_for_postcode.side_effect = SouthGlosBinsAPIError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert "Traceback" not in caplog.text


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


async def test_duplicate_aborts(hass: HomeAssistant, mock_api: AsyncMock) -> None:
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


async def test_invalid_postcode(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """A malformed postcode is rejected before calling the API."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "../../admin"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"postcode": "invalid_postcode"}
    mock_api.get_addresses_for_postcode.assert_not_awaited()


async def test_unexpected_error(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """An unexpected exception surfaces the unknown error."""
    mock_api.get_addresses_for_postcode.side_effect = RuntimeError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["errors"] == {"base": "unknown"}


async def test_single_address_without_collections(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """A lone address with no collections shows an error, then can recover."""
    mock_api.get_collection_data.return_value = {"collections": {}}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "no_collections"}

    mock_api.get_collection_data.return_value = {
        "collections": {"refuse": {"available": True}}
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_selected_address_without_collections(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """Picking an address with no collections keeps the user on the select step."""
    mock_api.get_addresses_for_postcode.return_value = [
        {"uprn": "1", "address": "Unit 1, BS1 1AA", "name": "Unit 1"},
        {"uprn": "2", "address": "2 Test Road, BS1 1AA", "name": "2 Test Road"},
    ]
    mock_api.get_collection_data.return_value = {"collections": {}}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"uprn": "1"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_address"
    assert result["errors"] == {"base": "no_collections"}


async def test_collection_check_cannot_connect(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    """A failure while checking collections surfaces cannot_connect."""
    mock_api.get_collection_data.side_effect = SouthGlosBinsAPIError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"postcode": "BS1 1AA"}
    )
    assert result["errors"] == {"base": "cannot_connect"}
