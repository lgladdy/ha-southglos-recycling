"""Config flow for the South Gloucestershire Recycling Collections integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import SouthGlosBinsAPI, SouthGlosBinsAPIError
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
            postcode = user_input[CONF_POSTCODE].strip().upper()
            api = SouthGlosBinsAPI(self.hass)
            try:
                addresses = await api.get_addresses_for_postcode(postcode)
            except SouthGlosBinsAPIError:
                _LOGGER.exception("Error connecting to the collections service")
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if not addresses:
                    errors["base"] = "no_addresses_found"
                elif len(addresses) == 1:
                    return await self._async_create_entry(addresses[0], postcode)
                else:
                    self._addresses = addresses
                    self._postcode = postcode
                    return await self.async_step_select_address()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle address selection when multiple addresses are found."""
        if user_input is not None:
            selected = next(
                addr
                for addr in self._addresses
                if str(addr["uprn"]) == user_input[CONF_UPRN]
            )
            return await self._async_create_entry(selected, self._postcode)

        return self.async_show_form(
            step_id="select_address",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPRN): vol.In(
                        {
                            str(addr["uprn"]): addr["address"]
                            for addr in self._addresses
                        }
                    )
                }
            ),
        )

    async def _async_create_entry(
        self, address: dict[str, Any], postcode: str
    ) -> ConfigFlowResult:
        """Create the config entry for the selected address."""
        uprn = str(address["uprn"])
        await self.async_set_unique_id(uprn)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=address["address"],
            data={CONF_UPRN: uprn, CONF_POSTCODE: postcode},
        )
