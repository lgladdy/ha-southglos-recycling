"""Tests for the sensor platform."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.southglos_bins.const import COLLECTIONS_API_URL

from .conftest import collections_payload, service


@pytest.mark.usefixtures("setup_integration")
async def test_sensors(hass: HomeAssistant) -> None:
    """Date and status sensors are created for each available collection."""
    assert hass.states.get("sensor.2_test_road_next_food_collection") is None

    refuse = hass.states.get("sensor.2_test_road_next_refuse_collection")
    assert refuse.state == "2026-11-10"
    assert refuse.attributes["days_until_collection"] == 21
    assert refuse.attributes["status"] == "In 21 days"
    # Collected earlier today, so it is still the collection day.
    assert refuse.attributes["is_collection_day"] is True

    recycling = hass.states.get("sensor.2_test_road_next_recycling_collection")
    assert recycling.state == "2026-10-20"
    assert recycling.attributes["status"] == "Today"

    status = hass.states.get("sensor.2_test_road_recycling_collection_status")
    assert status.state == "In Progress"
    assert status.attributes["icon"] == "mdi:truck"
    assert status.attributes["reason"] == "Street not yet completed"
    assert status.attributes["round"] == "CK 16 Tue"

    refuse_status = hass.states.get("sensor.2_test_road_refuse_collection_status")
    assert refuse_status.state == "Closed Completed"
    assert refuse_status.attributes["completed_time"].hour == 9


async def test_stale_date_shows_past(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A collection date in the past reports "Past" rather than a negative count."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(COLLECTIONS_API_URL, exc=TimeoutError())
    freezer.move_to("2026-10-29T12:00:00+00:00")
    await setup_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    # The failed refresh leaves the entity unavailable; restore data to check
    # the attribute calculation on stale values.
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        COLLECTIONS_API_URL,
        json={
            "value": [
                service(
                    "Garden",
                    hso_nextcollection="2026-10-27T07:00:00+00:00",
                    hso_lastcollection="2026-10-13T07:00:00+01:00",
                    hso_statename="Closed Completed",
                )
            ]
        },
    )
    await setup_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    garden = hass.states.get("sensor.2_test_road_next_garden_collection")
    assert garden.attributes["days_until_collection"] == -2
    assert garden.attributes["status"] == "Past"


async def test_new_collection_type_added(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A collection type that appears later gets entities without a reload."""
    assert hass.states.get("sensor.2_test_road_next_food_collection") is None

    payload = collections_payload()
    payload["value"].append(service("Food", hso_statename="Closed Completed"))
    aioclient_mock.clear_requests()
    aioclient_mock.get(COLLECTIONS_API_URL, json=payload)
    await setup_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.2_test_road_next_food_collection") is not None
    assert hass.states.get("calendar.2_test_road_food_collection") is not None


@pytest.mark.usefixtures("setup_integration")
async def test_unrecorded_attributes(hass: HomeAssistant) -> None:
    """Attributes that change on every poll are excluded from the recorder."""
    entity = hass.data["entity_components"]["sensor"].get_entity(
        "sensor.2_test_road_recycling_collection_status"
    )
    assert {"last_updated", "original_next_collection"} <= (
        entity._state_info["unrecorded_attributes"]
    )


async def test_long_status_truncated(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Free-text status longer than HA's state limit is truncated, not rejected."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        COLLECTIONS_API_URL,
        json={"value": [service("Recycling", hso_statename="x" * 400)]},
    )
    await setup_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.2_test_road_recycling_collection_status")
    assert state.state == "x" * 255
