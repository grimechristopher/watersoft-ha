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

    def _normalize_device_data(self, device: dict[str, Any]) -> dict[str, Any]:
        """Normalize device data from API to expected format.

        Args:
            device: Raw device data from API

        Returns:
            Normalized device data
        """
        # Map API fields (camelCase) to expected fields (snake_case)
        normalized = {
            "id": device.get("id"),
            "device_name": device.get("name", "Rainsoft Water Softener"),
            "model": device.get("model"),
            "serial_number": device.get("serialNumber"),
            "firmware_version": None,  # Not provided by API
            # Salt and capacity
            "salt_level": device.get("saltLbs", 0),
            "capacity_remaining": device.get("capacityRemaining", 0),
            # System status
            "system_status": device.get("systemStatusName", "unknown"),
            # Regeneration
            "last_regeneration": None,  # Not provided by API
            "next_regeneration": device.get("regenTime"),
            # Location info
            "location_id": device.get("location_id"),
            "location_name": device.get("location_name"),
        }

        # Calculate regeneration active from system status
        system_status = normalized["system_status"].lower() if normalized["system_status"] else ""
        normalized["regeneration_active"] = "regenerat" in system_status

        return normalized

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

            # Normalize device data (skip broken /device endpoint)
            device_data: dict[str, Any] = {}
            for device in devices:
                device_id = device.get("id")
                if not device_id:
                    _LOGGER.warning("Device missing ID: %s", device)
                    continue

                # Normalize the device data from /locations response
                normalized = self._normalize_device_data(device)
                device_data[str(device_id)] = normalized

                _LOGGER.debug(
                    "Updated device %s: salt=%s%%, capacity=%s%%, status=%s",
                    device_id,
                    normalized.get("salt_level"),
                    normalized.get("capacity_remaining"),
                    normalized.get("system_status"),
                )

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
