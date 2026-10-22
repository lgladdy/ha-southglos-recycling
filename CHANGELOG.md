# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0]

First release intended for the HACS default repository. Requires Home Assistant
2026.3 or newer.

### Added

- Brand icon shipped in `brand/` (local brand images, Home Assistant 2026.3+).
- Config flow validates the postcode and rejects addresses the council has no
  collections for (e.g. commercial units), instead of creating an empty entry.
- New collection types (e.g. a garden waste subscription started later) are
  picked up automatically without reloading the integration.
- Diagnostics download with UPRN, postcode and address redacted.
- Entity icons defined in `icons.json`.

- Device registry entry so all sensors and calendars for an address are grouped
  under a single device.
- Translated entity names via `translations/en.json`.
- `cannot_connect` config-flow error and duplicate-address protection
  (`async_set_unique_id` / abort if already configured).
- GitHub Actions workflows for hassfest, HACS validation, ruff and pytest.
- Test suite based on `pytest-homeassistant-custom-component`.

### Changed

- Minimum Home Assistant version is now 2026.3.0.
- New entries are titled with the house and street (e.g. "2 Westerleigh Road")
  rather than the full upper-case address, giving shorter entity IDs.
- Integration now stores its coordinator in `entry.runtime_data` with a typed
  config entry.
- Coordinator refreshes just after midnight via `async_track_time_change`
  instead of a five-minute polling loop.
- API client always uses Home Assistant's shared `aiohttp` session.
- Collection dates are converted to local time before taking the date, so a
  midnight sent in UTC during BST no longer lands a day early.

### Fixed

- Requests now time out after 30 seconds; timeouts and malformed JSON are
  reported as connection errors instead of unexpected exceptions.
- Null fields in the council's response no longer crash the parser.
- Addresses without a UPRN are skipped instead of creating a `None` entry.
- Calendar range queries no longer include an event that starts exactly at the
  end of the requested window.
- The date sensor's `status` attribute shows "Past" instead of "In -1 days"
  when council data is stale.
- `last_updated` and `original_next_collection` are no longer recorded on every
  poll.
- README calendar entity IDs and example card now match the real entity IDs.

### Removed

- `aiohttp` from `manifest.json` requirements (provided by Home Assistant core).
- Dead date-parsing helpers in the API client.

## [0.1.0]

- Initial release (its `manifest.json` reported version 1.0.0).
