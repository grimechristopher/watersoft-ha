"""Config flow for Rainsoft integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RainsoftApiClient, RainsoftAuthError, RainsoftConnectionError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def validate_credentials(
    hass: HomeAssistant, email: str, password: str
) -> dict[str, str]:
    """Validate credentials and return customer info.

    Args:
        hass: HomeAssistant instance
        email: Rainsoft account email
        password: Rainsoft account password

    Returns:
        Dictionary with customer info

    Raises:
        RainsoftAuthError: If authentication fails
        RainsoftConnectionError: If connection fails
    """
    session = async_get_clientsession(hass)
    api = RainsoftApiClient(session, email, password)

    # Authenticate
    await api.authenticate()

    # Get customer ID to verify account is valid
    customer_id = await api.get_customer_id()

    return {"customer_id": customer_id, "email": email.lower().strip()}


class RainsoftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rainsoft."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_credentials(
                    self.hass,
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )

                # Create unique ID from email to prevent duplicates
                await self.async_set_unique_id(info["email"])
                self._abort_if_unique_id_configured()

                # Create entry
                return self.async_create_entry(
                    title=info["email"],
                    data={
                        CONF_EMAIL: info["email"],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

            except RainsoftAuthError as err:
                _LOGGER.warning("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except RainsoftConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RainsoftOptionsFlow:
        """Get the options flow for this handler."""
        return RainsoftOptionsFlow(config_entry)


class RainsoftOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Rainsoft."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current scan interval from options (or use default)
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
