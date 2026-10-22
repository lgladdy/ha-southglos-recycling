"""API client for South Gloucestershire Bins."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import COLLECTION_TYPES, COLLECTIONS_API_URL, REQUEST_TIMEOUT, UPRN_API_URL

_LOGGER = logging.getLogger(__name__)

_POSTCODE_RE = re.compile(r"^([A-Z]{1,2}[0-9][A-Z0-9]?) ?([0-9][A-Z]{2})$")


class SouthGlosBinsAPIError(Exception):
    """Exception to indicate a general API error."""


def normalize_postcode(value: str) -> str | None:
    """Return a UK postcode in canonical ``AB1 2CD`` form, or None if invalid."""
    match = _POSTCODE_RE.match(value.strip().upper())
    if not match:
        return None
    return f"{match.group(1)} {match.group(2)}"


class SouthGlosBinsAPI:
    """API client for South Gloucestershire Bins."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self._session = async_get_clientsession(hass)

    async def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        """Fetch a URL and decode its JSON body."""
        try:
            async with self._session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise SouthGlosBinsAPIError(
                f"Error communicating with API: {err!r}"
            ) from err

    async def get_addresses_for_postcode(self, postcode: str) -> list[dict[str, Any]]:
        """Return the list of addresses known for a postcode.

        Each address has a ``uprn``, a full ``address`` for display and a short
        ``name`` (house and street) used as the entry title and device name.
        """
        data = await self._get_json(f"{UPRN_API_URL}/{quote(postcode, safe='')}")

        addresses: list[dict[str, Any]] = []
        if not isinstance(data, list):
            return addresses

        # The council returns upper-case parts; title-case them for display.
        for item in data:
            if not isinstance(item, dict) or not item.get("Uprn"):
                continue
            prop = (item.get("Property") or "").title()
            street = (item.get("Street") or "").title()
            parts = [
                prop,
                street,
                (item.get("Locality") or "").title(),
                (item.get("Town") or "").title(),
                (item.get("Postcode") or "").upper(),
            ]
            # "2 Westerleigh Road" but "Flat 1 Birch Court, Westerleigh Road".
            separator = " " if prop[:1].isdigit() else ", "
            name = separator.join(part for part in (prop, street) if part)
            addresses.append(
                {
                    "uprn": str(item["Uprn"]),
                    "address": ", ".join(part for part in parts if part),
                    "name": name or str(item["Uprn"]),
                }
            )

        return addresses

    async def get_collection_data(self, uprn: str) -> dict[str, Any]:
        """Return parsed collection data for a UPRN."""
        data = await self._get_json(COLLECTIONS_API_URL, params={"uprn": uprn})

        collections: dict[str, Any] = {}
        live_status: dict[str, Any] = {}

        services = data.get("value") if isinstance(data, dict) else None
        if isinstance(services, list):
            today = dt_util.now().date()
            for service in services:
                if not isinstance(service, dict):
                    continue
                service_name = (service.get("hso_servicename") or "").lower()
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
                    "schedule": service.get("hso_scheduledescription") or "",
                    "round": service.get("hso_round") or "",
                    "round_group": service.get("hso_roundgroup") or "",
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
        """Parse an ISO datetime string into a local calendar date."""
        parsed = SouthGlosBinsAPI._parse_datetime(value)
        return parsed.date() if parsed else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an ISO datetime string (e.g. ``2025-08-19T07:00:00+01:00``).

        Aware values are converted to Home Assistant's local time zone so that
        a midnight expressed in UTC during BST still lands on the right day.
        """
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError, AttributeError, TypeError:
            _LOGGER.warning("Could not parse datetime: %s", value)
            return None
        if parsed.tzinfo is None:
            return parsed
        return dt_util.as_local(parsed)
