"""Fixtures for the South Gloucestershire Recycling Collections tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in every test."""
    yield


@pytest.fixture
def mock_api() -> Generator[AsyncMock, None, None]:
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
            return_value=[{"uprn": "12345", "address": "1 Test Road, Bristol, BS1 1AA"}]
        )
        client.get_collection_data = AsyncMock(
            return_value={"collections": {}, "live_status": {}, "last_updated": None}
        )
        yield client
