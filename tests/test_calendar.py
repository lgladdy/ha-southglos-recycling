"""Tests for the calendar platform."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant


async def _get_events(
    hass: HomeAssistant, start: str, end: str
) -> list[dict[str, Any]]:
    entity_id = "calendar.2_test_road_garden_collection"
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": entity_id, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return response[entity_id]["events"]


@pytest.mark.usefixtures("setup_integration")
async def test_calendar_state(hass: HomeAssistant) -> None:
    """The calendar exposes the next collection as its upcoming event."""
    state = hass.states.get("calendar.2_test_road_garden_collection")
    assert state.attributes["message"] == "Garden Collection"
    assert state.attributes["start_time"] == "2026-10-27 00:00:00"
    assert "location" not in state.attributes or not state.attributes["location"]


@pytest.mark.usefixtures("setup_integration")
async def test_get_events(hass: HomeAssistant) -> None:
    """Next and last collections inside the window are returned in order."""
    events = await _get_events(
        hass, "2026-10-01T00:00:00+01:00", "2026-11-01T00:00:00+00:00"
    )
    assert [event["start"] for event in events] == ["2026-10-13", "2026-10-27"]
    assert "Schedule: Tuesday every other week" in events[1]["description"]


@pytest.mark.usefixtures("setup_integration")
async def test_get_events_window_end_is_exclusive(hass: HomeAssistant) -> None:
    """A window ending at the start of the collection day excludes it."""
    events = await _get_events(
        hass, "2026-10-20T00:00:00+01:00", "2026-10-27T00:00:00+00:00"
    )
    assert events == []
