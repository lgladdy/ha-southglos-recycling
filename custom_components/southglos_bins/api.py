"""API client for South Gloucestershire Bins."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import COLLECTION_TYPES, COLLECTIONS_API_URL, UPRN_API_URL

_LOGGER = logging.getLogger(__name__)


class SouthGlosBinsAPIError(Exception):
    """Exception to indicate a general API error."""


class SouthGlosBinsAPI:
    """API client for South Gloucestershire Bins."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self._session = async_get_clientsession(hass)

    async def get_addresses_for_postcode(self, postcode: str) -> list[dict[str, Any]]:
        """Return the list of addresses known for a postcode."""
        try:
            async with self._session.get(f"{UPRN_API_URL}/{postcode}") as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise SouthGlosBinsAPIError(f"Error communicating with API: {err}") from err

        addresses: list[dict[str, Any]] = []
        if isinstance(data, list):
            for item in data:
                address_parts = [
                    item.get("Property"),
                    item.get("Street"),
                    item.get("Locality"),
                    item.get("Town"),
                    item.get("Postcode"),
                ]
                full_address = ", ".join(part for part in address_parts if part)
                addresses.append({"uprn": item.get("Uprn"), "address": full_address})

        return addresses

    async def get_collection_data(self, uprn: str) -> dict[str, Any]:
        """Return parsed collection data for a UPRN."""
        try:
            async with self._session.get(
                COLLECTIONS_API_URL, params={"uprn": uprn}
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise SouthGlosBinsAPIError(f"Error communicating with API: {err}") from err

        collections: dict[str, Any] = {}
        live_status: dict[str, Any] = {}

        if isinstance(data, dict) and "value" in data:
            today = dt_util.now().date()
            for service in data["value"]:
                service_name = service.get("hso_servicename", "").lower()
                if service_name not in COLLECTION_TYPES:
                    continue

                next_collection_date = self._parse_date(
                    service.get("hso_nextcollection")
                )
                last_collection_date = self._parse_date(
                    service.get("hso_lastcollection")
                )
                last_completed = self._parse_datetime(
                    service.get("hso_lastcollectioncompleted")
                )
                state_name = service.get("hso_statename")

                # If the last collection is today and the round has not been
                # closed off yet, today is effectively the collection day.
                actual_next_collection = next_collection_date
                if (
                    last_collection_date == today
                    and state_name
                    and state_name.lower() != "closed completed"
                ):
                    actual_next_collection = today

                collections[service_name] = {
                    "next_collection": actual_next_collection,
                    "last_collection": last_collection_date,
                    "last_completed": last_completed,
                    "original_next_collection": next_collection_date,
                    "available": True,
                    "schedule": service.get("hso_scheduledescription", ""),
                    "round": service.get("hso_round", ""),
                    "round_group": service.get("hso_roundgroup", ""),
                }

                if state_name:
                    live_status[service_name] = {
                        "status": state_name,
                        "reason": service.get("hso_reason"),
                        "source": service.get("hso_statesource"),
                    }

        return {
            "collections": collections,
            "live_status": live_status,
            "last_updated": dt_util.now(),
        }

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Parse an ISO datetime string into a date."""
        parsed = SouthGlosBinsAPI._parse_datetime(value)
        return parsed.date() if parsed else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an ISO datetime string (e.g. ``2025-08-19T07:00:00+01:00``)."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            _LOGGER.warning("Could not parse datetime: %s", value)
            return None
