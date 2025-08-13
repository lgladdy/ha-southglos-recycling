# South Gloucestershire Recycling Collections Integration

This is a Home Assistant custom integration for tracking bin collection schedules in South Gloucestershire.

## Project Structure

```
custom_components/southglos_bins/
├── __init__.py              # Main integration setup and entry point
├── api.py                   # REST API client for UPRN lookup and collection data
├── config_flow.py           # Configuration flow for postcode setup
├── const.py                 # Constants and configuration values
├── coordinator.py           # Data update coordinator with smart scheduling
├── manifest.json            # Integration metadata and requirements
├── sensor.py                # Sensor entities for collection dates and live status
└── strings.json             # UI text and error messages
```

## Key Features

- **Postcode-based setup**: Users enter postcode to automatically find UPRN
- **Multi-address support**: Handles multiple addresses per postcode
- **Smart update scheduling**: 
  - Daily updates normally (24 hours)
  - 15-minute updates on collection days for live status
- **Collection types**: Refuse, Recycling, Food, Garden (when available)
- **Intelligent date handling**: Recognizes collection days when either scheduled for today OR when collection happened/is happening today with live status
- **Completion time tracking**: Captures and displays the exact time when collections were completed
- **Two sensor types per collection**:
  - Date sensor: Shows next collection date with days remaining
  - Status sensor: Live collection status with reason and round information

## API Endpoints Used

- UPRN Lookup: `https://webapps.southglos.gov.uk/Webservices/SGC.RefuseCollectionService/RefuseCollectionService.svc/getAddresses/{postcode}`
- Collection Data: `https://api.southglos.gov.uk/wastecomp/GetCollectionDetails?uprn={uprn}`

## Sensor States

### Collection Date Sensors
- **State**: Next collection date (YYYY-MM-DD format)
- **Attributes**:
  - `days_until_collection`: Number of days until next collection
  - `status`: Human-readable status ("Today", "Tomorrow", "In X days")
  - `is_collection_day`: Boolean indicating if today is collection day

### Live Status Sensors
- **State**: Live collection status ("In Progress", "Closed Completed", etc.)
- **Attributes**:
  - `is_collection_day`: Boolean indicating if today is collection day
  - `collection_type`: The type of collection being tracked
  - `reason`: Status reason (e.g., "Street not yet completed")
  - `schedule`: Collection schedule (e.g., "Wednesday every week")
  - `round`: Collection round (e.g., "CK 14 Wed")
  - `round_group`: Round group (e.g., "Recycling CK 14")
  - `completed_time`: Exact datetime when collection was completed (if applicable)
  - `last_updated`: When data was last refreshed

## Dependencies

- `aiohttp`: For REST API calls
- Home Assistant core sensor platform
- Home Assistant config flow system

## Configuration

Integration is configured through the Home Assistant UI:
1. Add integration "South Gloucestershire Recycling Collections"
2. Enter postcode
3. Select address if multiple found
4. Integration automatically creates sensors for available collection types

## Sample Dashboard Cards

See `example-card.yaml` for a complete dashboard configuration that:
- Automatically handles missing collection types (e.g., addresses without Food collections)
- Shows a "Collection Day Active" banner when live tracking is enabled
- Displays upcoming collections with days remaining on normal days
- Switches to live status tracking with completion times on collection days
- Uses only default Home Assistant cards (no custom components required)


## Error Handling

- API connection errors are handled gracefully
- Invalid postcodes show appropriate error messages
- Missing or unavailable collection types are filtered out
- Update failures are logged and retried on next scheduled update