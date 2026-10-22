"""Fixtures for the South Gloucestershire Recycling Collections tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.southglos_bins.const import COLLECTIONS_API_URL, DOMAIN

UPRN = "12345"

# Tuesday 20 October 2026, 10:00 BST: a refuse and recycling collection day.
NOW = "2026-10-20T10:00:00+01:00"


def service(name: str | None, **overrides: Any) -> dict[str, Any]:
    """Return one service record shaped like the council's API response."""
    record = {
        "hso_servicename": name,
        "hso_nextcollection": "2026-10-27T07:00:00+00:00",
        "hso_lastcollection": "2026-10-20T07:00:00+01:00",
        "hso_lastcollectioncompleted": None,
        "hso_statename": "In Progress",
        "hso_reason": "Street not yet completed",
        "hso_statesource": "RoundLegInstance",
        "hso_scheduledescription": "Tuesday every week",
        "hso_round": "CK 16 Tue",
        "hso_roundgroup": "Recycling CK 16",
        "hso_uprn": UPRN,
    }
    record.update(overrides)
    return record


def collections_payload() -> dict[str, Any]:
    """Return a council response with refuse, recycling and garden services."""
    return {
        "value": [
            service(
                "Refuse",
                hso_nextcollection="2026-11-10T00:00:00+00:00",
                hso_lastcollectioncompleted="2026-10-20T09:02:03+01:00",
                hso_statename="Closed Completed",
                hso_reason="Outside time allowed",
                hso_scheduledescription="Tuesday every 3rd week",
                hso_round="CR 02 Tue A",
                hso_roundgroup="Refuse CR 02",
            ),
            service("Recycling"),
            service(
                "Garden",
                hso_lastcollection="2026-10-13T07:00:00+01:00",
                hso_statename="Closed Completed",
                hso_scheduledescription="Tuesday every other week",
                hso_round="CG 01 Tue B",
                hso_roundgroup="Garden CG 01",
            ),
        ]
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in every test."""
    yield


@pytest.fixture
async def london(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Run in the UK time zone on a collection day."""
    await hass.config.async_set_time_zone("Europe/London")
    freezer.move_to(NOW)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for a test address."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=UPRN,
        title="2 Test Road",
        data={"uprn": UPRN, "postcode": "BS16 6AA"},
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    london: None,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up the integration against a mocked council API."""
    aioclient_mock.get(COLLECTIONS_API_URL, json=collections_payload())
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Mock the South Gloucestershire API client."""
    with (
        patch(
            "custom_components.southglos_bins.config_flow.SouthGlosBinsAPI",
            autospec=True,
        ) as flow_api,
        patch(
            "custom_components.southglos_bins.coordinator.SouthGlosBinsAPI",
            autospec=True,
        ) as coord_api,
    ):
        client = flow_api.return_value
        coord_api.return_value = client
        client.get_addresses_for_postcode = AsyncMock(
            return_value=[
                {
                    "uprn": UPRN,
                    "address": "2 Test Road, Downend, BS16 6AA",
                    "name": "2 Test Road",
                }
            ]
        )
        client.get_collection_data = AsyncMock(
            return_value={
                "collections": {"refuse": {"available": True}},
                "live_status": {},
                "last_updated": None,
            }
        )
        yield client
