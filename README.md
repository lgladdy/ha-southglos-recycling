# South Gloucestershire Recycling Collections

A Home Assistant custom integration for tracking bin collection schedules in South Gloucestershire, UK.

## Features

🗑️ **Collection Tracking** - Monitor Refuse, Recycling, Food, and Garden collections  
📅 **Smart Scheduling** - Daily updates normally, 15-minute updates on collection days  
🚛 **Live Status** - Real-time collection progress when bins are being collected  
⏰ **Completion Times** - See exactly when your bins were collected  
🏠 **Address-Specific** - Only shows collections available for your specific address  
🎯 **Collection Day Detection** - Automatically identifies when collections are happening

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/lgladdy/ha-southglos-recycling`
6. Category: "Integration"
7. Click "Add"
8. Find "South Gloucestershire Recycling Collections" and click "Install"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/southglos_bins` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services**
2. Click **"Add Integration"**
3. Search for **"South Gloucestershire Recycling Collections"**
4. Enter your **postcode** (e.g., "BS16 7AE")
5. If multiple addresses are found, select your specific address
6. The integration will create sensors for your available collection types

## Sensors Created

For each available collection type, two sensors are created:

### Collection Date Sensors
- `sensor.next_refuse_collection` - Next refuse collection date
- `sensor.next_recycling_collection` - Next recycling collection date  
- `sensor.next_food_collection` - Next food collection date (if available)
- `sensor.next_garden_collection` - Next garden collection date (if available)

**Attributes include:**
- `days_until_collection` - Number of days until next collection
- `status` - Human-readable status ("Today", "Tomorrow", "In X days")
- `is_collection_day` - Whether today is a collection day

### Live Status Sensors
- `sensor.refuse_collection_status` - Live refuse collection status
- `sensor.recycling_collection_status` - Live recycling collection status
- `sensor.food_collection_status` - Live food collection status (if available)
- `sensor.garden_collection_status` - Live garden collection status (if available)

**Attributes include:**
- `reason` - Status reason (e.g., "Street not yet completed")
- `schedule` - Collection schedule (e.g., "Wednesday every week")
- `round` - Collection round (e.g., "CK 14 Wed")
- `completed_time` - Exact time collection was completed (when applicable)

## Dashboard Cards

The integration includes an example dashboard configuration in `example-card.yaml`:

- **Collection Day Banner** - Shows when live tracking is active
- **Upcoming Collections** - Displays next collection dates with countdown
- **Live Status Cards** - Real-time collection progress on collection days
- **Completion Times** - Shows when collections were completed

Copy the configuration from `example-card.yaml` into your Home Assistant dashboard.

## How It Works

The integration connects to South Gloucestershire Council's waste management system:

1. **Address Lookup** - Uses your postcode to find your UPRN (Unique Property Reference Number)
2. **Collection Data** - Retrieves your specific collection schedule and live status
3. **Smart Updates** - Updates daily normally, every 15 minutes on collection days
4. **Collection Day Detection** - Recognizes when collections are scheduled or happening today
5. **Live Tracking** - Shows real-time progress: "In Progress", "Closed Completed", etc.

## API Endpoints

- **Address Lookup**: `https://webapps.southglos.gov.uk/Webservices/SGC.RefuseCollectionService/RefuseCollectionService.svc/getAddresses/{postcode}`
- **Collection Data**: `https://api.southglos.gov.uk/wastecomp/GetCollectionDetails?uprn={uprn}`

## Collection Types

- **Refuse** 🗑️ - General household waste
- **Recycling** ♻️ - Recyclable materials  
- **Food** 🍎 - Food waste (not available at all addresses)
- **Garden** 🌳 - Garden waste (seasonal/subscription service)

## Example Dashboard Display

### Normal Day
```
Upcoming Collections
🗑️ Refuse: 2025-08-20 - In 7 days
♻️ Recycling: 2025-08-20 - In 7 days  
🌳 Garden: 2025-08-19 - In 6 days
```

### Collection Day
```
🚛 Collection Day Active
Live tracking enabled - Status updates every 15 minutes

Collections today:
- ♻️ Recycling: Closed Completed (completed 4:25 PM)

♻️ Recycling Collection - TODAY
Status: Closed Completed
Next Scheduled: 2025-08-27
```

## Troubleshooting

### No Collections Showing
- Verify your postcode is correct
- Check that collections are available for your address
- Some addresses may not have all collection types (e.g., Food collections)

### Integration Not Loading
- Restart Home Assistant after installation
- Check the Home Assistant logs for errors
- Ensure your Home Assistant can access external APIs

### Incorrect Collection Dates
- The integration shows data directly from South Gloucestershire Council
- Collection dates may change due to bank holidays or service disruptions
- Data updates automatically every 24 hours

## Support

- Check existing issues: [GitHub Issues](https://github.com/lgladdy/ha-southglos-recycling/issues)
- Create a new issue for bugs or feature requests
- Include your Home Assistant logs when reporting issues

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with South Gloucestershire Council. It uses publicly available APIs to provide collection information. The accuracy of data depends on the council's systems.