"""Data coordinator for Rainsoft integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    RainsoftApiClient,
    RainsoftApiError,
    RainsoftAuthError,
    RainsoftConnectionError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RainsoftDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Rainsoft data from API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: RainsoftApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize coordinator.

        Args:
            hass: HomeAssistant instance
            api: Rainsoft API client
            update_interval: Update interval timedelta
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api
        self.devices: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API.

        Returns:
            Dictionary mapping device IDs to device data

        Raises:
            ConfigEntryAuthFailed: If authentication fails
            UpdateFailed: If update fails
        """
        try:
            # Get all devices for this account
            devices = await self.api.get_devices()

            if not devices:
                _LOGGER.warning("No devices found for this account")
                return {}

            # Store devices list for entity setup
            self.devices = devices

            # Fetch status for each device
            device_data: dict[str, Any] = {}
            for device in devices:
                device_id = device.get("id")
                if not device_id:
                    _LOGGER.warning("Device missing ID: %s", device)
                    continue

                try:
                    # Get current status
                    status = await self.api.get_device_status(str(device_id))

                    # Merge device info with status
                    device_data[str(device_id)] = {
                        **device,
                        **status,
                    }

                    _LOGGER.debug(
                        "Updated device %s: salt=%s%%, capacity=%s%%, status=%s",
                        device_id,
                        status.get("salt_level"),
                        status.get("capacity_remaining"),
                        status.get("system_status"),
                    )

                except RainsoftApiError as err:
                    _LOGGER.warning(
                        "Failed to fetch status for device %s: %s", device_id, err
                    )
                    # Continue with other devices even if one fails
                    continue

            if not device_data:
                raise UpdateFailed("No device data available")

            return device_data

        except RainsoftAuthError as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise ConfigEntryAuthFailed("Authentication failed") from err

        except RainsoftConnectionError as err:
            _LOGGER.error("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err

        except RainsoftApiError as err:
            _LOGGER.error("API error: %s", err)
            raise UpdateFailed(f"API error: {err}") from err

        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err
