"""API client for South Gloucestershire Bins."""
from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from .const import UPRN_API_URL, COLLECTIONS_API_URL

_LOGGER = logging.getLogger(__name__)


class SouthGlosBinsAPIError(Exception):
    """Exception to indicate a general API error."""


class SouthGlosBinsAPI:
    """API client for South Gloucestershire Bins."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get aiohttp session."""
        if self._session is None:
            if self._hass:
                self._session = async_get_clientsession(self._hass)
            else:
                self._session = aiohttp.ClientSession()
        return self._session

    async def get_addresses_for_postcode(self, postcode: str) -> list[dict[str, Any]]:
        """Get addresses for a postcode."""
        session = await self._get_session()
        
        try:
            async with session.get(
                f"{UPRN_API_URL}/{postcode}"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Handle the response format from South Gloucestershire API
                addresses = []
                if isinstance(data, list):
                    for item in data:
                        # Build full address string from components
                        address_parts = []
                        if item.get("Property"):
                            address_parts.append(item["Property"])
                        if item.get("Street"):
                            address_parts.append(item["Street"])
                        if item.get("Locality"):
                            address_parts.append(item["Locality"])
                        if item.get("Town"):
                            address_parts.append(item["Town"])
                        if item.get("Postcode"):
                            address_parts.append(item["Postcode"])
                        
                        full_address = ", ".join(filter(None, address_parts))
                        
                        addresses.append({
                            "uprn": item.get("Uprn"),
                            "address": full_address
                        })
                
                return addresses
                
        except aiohttp.ClientError as err:
            raise SouthGlosBinsAPIError(f"Error communicating with API: {err}") from err

    async def get_collection_data(self, uprn: str) -> dict[str, Any]:
        """Get collection data for a UPRN."""
        session = await self._get_session()
        
        try:
            async with session.get(
                COLLECTIONS_API_URL,
                params={"uprn": uprn}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Parse the South Gloucestershire OData response
                collections = {}
                live_status = {}
                
                if isinstance(data, dict) and "value" in data:
                    for service in data["value"]:
                        service_name = service.get("hso_servicename", "").lower()
                        
                        # Map service names to our collection types
                        if service_name in ["refuse", "recycling", "food", "garden"]:
                            # Parse dates
                            next_collection_str = service.get("hso_nextcollection")
                            last_collection_str = service.get("hso_lastcollection")
                            last_completed_str = service.get("hso_lastcollectioncompleted")
                            state_name = service.get("hso_statename")
                            
                            next_collection_date = self._parse_datetime(next_collection_str)
                            last_collection_date = self._parse_datetime(last_collection_str)
                            last_completed_datetime = self._parse_datetime_full(last_completed_str)
                            
                            # Determine actual next collection date
                            # If last collection is today and status is not "Closed Completed", 
                            # then today is the collection day
                            actual_next_collection = next_collection_date
                            today = date.today()
                            
                            if (last_collection_date == today and 
                                state_name and 
                                state_name.lower() != "closed completed"):
                                # Collection is today and in progress
                                actual_next_collection = today
                            
                            collections[service_name] = {
                                "next_collection": actual_next_collection,
                                "last_collection": last_collection_date,
                                "last_completed": last_completed_datetime,
                                "original_next_collection": next_collection_date,
                                "available": True,
                                "schedule": service.get("hso_scheduledescription", ""),
                                "round": service.get("hso_round", ""),
                                "round_group": service.get("hso_roundgroup", "")
                            }
                            
                            # Live status information
                            state_name = service.get("hso_statename")
                            reason = service.get("hso_reason")
                            
                            if state_name:
                                live_status[service_name] = {
                                    "status": state_name,
                                    "reason": reason,
                                    "source": service.get("hso_statesource")
                                }
                
                return {
                    "collections": collections,
                    "live_status": live_status,
                    "last_updated": datetime.now()
                }
                
        except aiohttp.ClientError as err:
            raise SouthGlosBinsAPIError(f"Error communicating with API: {err}") from err

    def _parse_datetime(self, date_str: str | None) -> date | None:
        """Parse datetime string to date object."""
        if not date_str:
            return None
        
        try:
            # Handle ISO datetime format from South Gloucestershire API
            # e.g., "2025-08-19T07:00:00+01:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, AttributeError):
            _LOGGER.warning("Could not parse datetime: %s", date_str)
            return None

    def _parse_datetime_full(self, date_str: str | None) -> datetime | None:
        """Parse datetime string to full datetime object."""
        if not date_str:
            return None
        
        try:
            # Handle ISO datetime format from South Gloucestershire API
            # e.g., "2025-08-13T16:25:59+01:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt
        except (ValueError, AttributeError):
            _LOGGER.warning("Could not parse datetime: %s", date_str)
            return None

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date string to date object."""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            _LOGGER.warning("Could not parse date: %s", date_str)
            return None

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._hass:
            await self._session.close()