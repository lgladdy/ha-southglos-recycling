"""Constants for the South Gloucestershire Bins integration."""

DOMAIN = "southglos_bins"

CONF_UPRN = "uprn"

API_BASE_URL = "https://webapps.southglos.gov.uk/Webservices/SGC.RefuseCollectionService/RefuseCollectionService.svc"
UPRN_API_URL = f"{API_BASE_URL}/getAddresses"
COLLECTIONS_API_URL = "https://api.southglos.gov.uk/wastecomp/GetCollectionDetails"

UPDATE_INTERVAL_NORMAL = 24 * 60 * 60  # 24 hours in seconds
UPDATE_INTERVAL_COLLECTION_DAY = 15 * 60  # 15 minutes in seconds

COLLECTION_TYPES = ["refuse", "recycling", "food", "garden"]