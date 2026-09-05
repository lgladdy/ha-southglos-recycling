"""Constants for the South Gloucestershire Bins integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "southglos_bins"

CONF_UPRN: Final = "uprn"
CONF_POSTCODE: Final = "postcode"

MANUFACTURER: Final = "South Gloucestershire Council"

API_BASE_URL: Final = (
    "https://webapps.southglos.gov.uk/Webservices/SGC.RefuseCollectionService"
    "/RefuseCollectionService.svc"
)
UPRN_API_URL: Final = f"{API_BASE_URL}/getAddresses"
COLLECTIONS_API_URL: Final = "https://api.southglos.gov.uk/wastecomp/GetCollectionDetails"

UPDATE_INTERVAL_NORMAL: Final = 24 * 60 * 60  # 24 hours in seconds
UPDATE_INTERVAL_COLLECTION_DAY: Final = 15 * 60  # 15 minutes in seconds

COLLECTION_TYPES: Final = ["refuse", "recycling", "food", "garden"]

COLLECTION_ICONS: Final = {
    "refuse": "mdi:delete",
    "recycling": "mdi:recycle",
    "food": "mdi:food-apple",
    "garden": "mdi:tree",
}
