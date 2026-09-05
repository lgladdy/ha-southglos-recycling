# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Device registry entry so all sensors and calendars for an address are grouped
  under a single device.
- Translated entity names via `translations/en.json`.
- `cannot_connect` config-flow error and duplicate-address protection
  (`async_set_unique_id` / abort if already configured).
- GitHub Actions workflows for hassfest, HACS validation, ruff and pytest.
- Test suite based on `pytest-homeassistant-custom-component`.

### Changed

- Integration now stores its coordinator in `entry.runtime_data` with a typed
  config entry.
- Coordinator refreshes just after midnight via `async_track_time_change`
  instead of a five-minute polling loop.
- API client always uses Home Assistant's shared `aiohttp` session.

### Removed

- `aiohttp` from `manifest.json` requirements (provided by Home Assistant core).
- Dead date-parsing helpers in the API client.

## [1.0.0]

- Initial release.
