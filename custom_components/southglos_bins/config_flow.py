"""Config flow for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import SouthGlosBinsAPI, SouthGlosBinsAPIError, normalize_postcode
from .const import CONF_POSTCODE, CONF_UPRN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_POSTCODE): str})


class SouthGlosBinsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for South Gloucestershire Recycling Collections."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._addresses: list[dict[str, Any]] = []
        self._postcode: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            postcode = normalize_postcode(user_input[CONF_POSTCODE])
            if postcode is None:
                errors[CONF_POSTCODE] = "invalid_postcode"
            else:
                api = SouthGlosBinsAPI(self.hass)
                try:
                    addresses = await api.get_addresses_for_postcode(postcode)
                except SouthGlosBinsAPIError:
                    _LOGGER.exception("Error connecting to the collections service")
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    self._postcode = postcode
                    if not addresses:
                        errors["base"] = "no_addresses_found"
                    elif len(addresses) == 1:
                        error = await self._async_validate_address(addresses[0])
                        if error is None:
                            return await self._async_create_entry(addresses[0])
                        errors["base"] = error
                    else:
                        self._addresses = addresses
                        return await self.async_step_select_address()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_select_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle address selection when multiple addresses are found."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = next(
                addr
                for addr in self._addresses
                if addr["uprn"] == user_input[CONF_UPRN]
            )
            error = await self._async_validate_address(selected)
            if error is None:
                return await self._async_create_entry(selected)
            errors["base"] = error

        return self.async_show_form(
            step_id="select_address",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPRN): vol.In(
                        {addr["uprn"]: addr["address"] for addr in self._addresses}
                    )
                }
            ),
            errors=errors,
        )

    async def _async_validate_address(self, address: dict[str, Any]) -> str | None:
        """Check the address has collections; return an error key if not."""
        api = SouthGlosBinsAPI(self.hass)
        try:
            data = await api.get_collection_data(address["uprn"])
        except SouthGlosBinsAPIError:
            _LOGGER.exception("Error connecting to the collections service")
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return "unknown"
        if not data["collections"]:
            return "no_collections"
        return None

    async def _async_create_entry(self, address: dict[str, Any]) -> ConfigFlowResult:
        """Create the config entry for the selected address."""
        await self.async_set_unique_id(address["uprn"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=address["name"],
            data={CONF_UPRN: address["uprn"], CONF_POSTCODE: self._postcode},
        )
