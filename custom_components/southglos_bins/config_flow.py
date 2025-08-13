"""Config flow for South Gloucestershire Bins integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import SouthGlosBinsAPI
from .const import DOMAIN, CONF_UPRN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("postcode"): str,
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for South Gloucestershire Bins."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            postcode = user_input["postcode"].strip().upper()
            
            try:
                api = SouthGlosBinsAPI()
                addresses = await api.get_addresses_for_postcode(postcode)
                
                if not addresses:
                    errors["base"] = "no_addresses_found"
                elif len(addresses) == 1:
                    # Single address found, use it
                    uprn = addresses[0]["uprn"]
                    title = f"{addresses[0]['address']}"
                    
                    return self.async_create_entry(
                        title=title,
                        data={CONF_UPRN: uprn, "postcode": postcode},
                    )
                else:
                    # Multiple addresses found, let user choose
                    self._addresses = addresses
                    self._postcode = postcode
                    return await self.async_step_select_address()
                    
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_address(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle address selection when multiple addresses are found."""
        if user_input is not None:
            selected_address = next(
                addr for addr in self._addresses if addr["uprn"] == user_input["address"]
            )
            
            return self.async_create_entry(
                title=selected_address["address"],
                data={CONF_UPRN: selected_address["uprn"], "postcode": self._postcode},
            )

        address_options = {
            addr["uprn"]: addr["address"] for addr in self._addresses
        }

        return self.async_show_form(
            step_id="select_address",
            data_schema=vol.Schema({
                vol.Required("address"): vol.In(address_options),
            }),
        )