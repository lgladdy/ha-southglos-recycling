"""Tests for the South Gloucestershire API client."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.southglos_bins.api import (
    SouthGlosBinsAPI,
    SouthGlosBinsAPIError,
    normalize_postcode,
)
from custom_components.southglos_bins.const import COLLECTIONS_API_URL, UPRN_API_URL

from .conftest import UPRN, collections_payload, service


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("bs16 6aa", "BS16 6AA"),
        ("  BS166AA ", "BS16 6AA"),
        ("BS37 4AB", "BS37 4AB"),
        ("SW1A 1AA", "SW1A 1AA"),
        ("M1 1AE", "M1 1AE"),
        ("not a postcode", None),
        ("BS16 6AA/../x", None),
        ("", None),
    ],
)
def test_normalize_postcode(value: str, expected: str | None) -> None:
    """Postcodes are validated and canonicalised."""
    assert normalize_postcode(value) == expected


async def test_addresses_parsed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Addresses are title-cased, named and filtered; the postcode is encoded."""
    aioclient_mock.get(
        f"{UPRN_API_URL}/BS16%206AA",
        json=[
            {
                "Property": "2",
                "Street": "WESTERLEIGH ROAD",
                "Locality": "",
                "Town": "DOWNEND",
                "Postcode": "BS16 6AA",
                "Uprn": "607693",
            },
            {
                "Property": "FLAT 1 BIRCH COURT",
                "Street": "WESTERLEIGH ROAD",
                "Locality": None,
                "Town": "DOWNEND",
                "Postcode": "BS16 6AA",
                "Uprn": 607694,
            },
            {"Property": "NO UPRN", "Street": "WESTERLEIGH ROAD", "Uprn": None},
            "not a dict",
        ],
    )

    addresses = await SouthGlosBinsAPI(hass).get_addresses_for_postcode("BS16 6AA")

    assert addresses == [
        {
            "uprn": "607693",
            "address": "2, Westerleigh Road, Downend, BS16 6AA",
            "name": "2 Westerleigh Road",
        },
        {
            "uprn": "607694",
            "address": "Flat 1 Birch Court, Westerleigh Road, Downend, BS16 6AA",
            "name": "Flat 1 Birch Court, Westerleigh Road",
        },
    ]


async def test_addresses_non_list(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An unexpected response shape yields no addresses."""
    aioclient_mock.get(f"{UPRN_API_URL}/BS16%206AA", json={"error": "nope"})
    assert await SouthGlosBinsAPI(hass).get_addresses_for_postcode("BS16 6AA") == []


@pytest.mark.parametrize(
    "mock_kwargs",
    [
        {"exc": TimeoutError()},
        {"status": 500},
        {"text": "<html>Service Unavailable</html>"},
    ],
    ids=["timeout", "http_error", "invalid_json"],
)
async def test_errors_raise_api_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_kwargs: dict
) -> None:
    """Timeouts, HTTP errors and bad JSON all surface as SouthGlosBinsAPIError."""
    aioclient_mock.get(COLLECTIONS_API_URL, **mock_kwargs)
    with pytest.raises(SouthGlosBinsAPIError):
        await SouthGlosBinsAPI(hass).get_collection_data(UPRN)


@pytest.mark.usefixtures("london")
async def test_collection_data_parsed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Services are parsed into collections and live status."""
    payload = collections_payload()
    payload["value"] += [service(None), service("Bulky"), "junk"]
    aioclient_mock.get(COLLECTIONS_API_URL, json=payload)

    data = await SouthGlosBinsAPI(hass).get_collection_data(UPRN)

    assert set(data["collections"]) == {"refuse", "recycling", "garden"}
    refuse = data["collections"]["refuse"]
    # Closed off today, so the next collection is the scheduled one.
    assert refuse["next_collection"] == date(2026, 11, 10)
    assert refuse["last_collection"] == date(2026, 10, 20)
    assert refuse["last_completed"] == datetime(
        2026, 10, 20, 9, 2, 3, tzinfo=dt_util.get_default_time_zone()
    )
    # Still in progress today, so today counts as the next collection.
    recycling = data["collections"]["recycling"]
    assert recycling["next_collection"] == date(2026, 10, 20)
    assert recycling["original_next_collection"] == date(2026, 10, 27)
    assert data["live_status"]["recycling"] == {
        "status": "In Progress",
        "reason": "Street not yet completed",
        "source": "RoundLegInstance",
    }


@pytest.mark.usefixtures("london")
async def test_null_fields(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Null strings and dates don't crash the parser."""
    aioclient_mock.get(
        COLLECTIONS_API_URL,
        json={
            "value": [
                service(
                    "Food",
                    hso_nextcollection=None,
                    hso_lastcollection="garbage",
                    hso_statename=None,
                    hso_scheduledescription=None,
                    hso_round=None,
                    hso_roundgroup=None,
                )
            ]
        },
    )

    data = await SouthGlosBinsAPI(hass).get_collection_data(UPRN)

    food = data["collections"]["food"]
    assert food["next_collection"] is None
    assert food["last_collection"] is None
    assert food["schedule"] == food["round"] == food["round_group"] == ""
    assert data["live_status"] == {}


@pytest.mark.usefixtures("london")
async def test_utc_midnight_in_bst_uses_local_date(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Midnight BST sent as 23:00 UTC the previous day maps to the local date."""
    aioclient_mock.get(
        COLLECTIONS_API_URL,
        json={
            "value": [
                service(
                    "Refuse",
                    hso_nextcollection="2026-07-14T23:00:00+00:00",
                    hso_statename="Closed Completed",
                )
            ]
        },
    )

    data = await SouthGlosBinsAPI(hass).get_collection_data(UPRN)

    assert data["collections"]["refuse"]["next_collection"] == date(2026, 7, 15)
