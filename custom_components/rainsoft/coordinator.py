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
        """Initialize coordinator."""
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

        Accepts data from either /locations (uses "id") or /device/{id} (uses "deviceId").
        """
        salt_lbs = int(device.get("saltLbs") or 0)
        max_salt = int(device.get("maxSalt") or 0)
        salt_level = min(round(salt_lbs / max_salt * 100), 100) if max_salt else None

        dealer = device.get("dealer") or {}

        normalized = {
            "id": device.get("id") or device.get("deviceId"),
            "device_name": device.get("name", "Rainsoft Water Softener"),
            "model": device.get("model"),
            "serial_number": device.get("serialNumber"),
            "firmware_version": device.get("firmwareVersion"),
            # Salt
            "salt_lbs": salt_lbs,
            "max_salt": max_salt,
            "salt_level": salt_level,
            "salt_28day": int(device.get("salt28Day") or 0),
            # Capacity and water usage
            "capacity_remaining": int(device.get("capacityRemaining") or 0),
            "daily_water_use": int(device.get("dailyWaterUse") or 0),
            "water_28day": int(device.get("water28Day") or 0),
            "flow_since_last_regen": int(device.get("flowSinceLastRegen") or 0),
            "lifetime_flow": int(device.get("lifeTimeFlow") or 0),
            # System status
            "system_status": device.get("systemStatusName", "unknown"),
            "hardness": int(device.get("hardness") or 0),
            # Regeneration
            "last_regeneration": device.get("lastRegenDate"),
            "next_regeneration": device.get("regenTime"),
            "regens_28day": int(device.get("regens28Day") or 0),
            "regens_this_month": int(device.get("regensThisMonth") or 0),
            # Dealer
            "dealer_name": dealer.get("name"),
            "dealer_phone": dealer.get("phone"),
            "dealer_email": dealer.get("email"),
            # Location info
            "location_id": device.get("location_id"),
            "location_name": device.get("location_name"),
        }

        system_status = normalized["system_status"].lower() if normalized["system_status"] else ""
        normalized["regeneration_active"] = "regenerat" in system_status and "queued" not in system_status

        return normalized

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            devices = await self.api.get_devices()

            if not devices:
                _LOGGER.warning("No devices found for this account")
                return {}

            self.devices = devices

            device_data: dict[str, Any] = {}
            for device in devices:
                device_id = device.get("id")
                if not device_id:
                    _LOGGER.warning("Device missing ID: %s", device)
                    continue

                # Try to get full detail from /device/{id} endpoint
                try:
                    detail = await self.api.get_device_detail(str(device_id))
                    normalized = self._normalize_device_data(detail)
                    # Preserve location info from the locations response
                    normalized["location_id"] = device.get("location_id")
                    normalized["location_name"] = device.get("location_name")
                    normalized["id"] = str(device_id)
                except Exception as err:
                    _LOGGER.warning("Device detail fetch failed for %s, using basic data: %s", device_id, err)
                    normalized = self._normalize_device_data(device)

                device_data[str(device_id)] = normalized

                _LOGGER.debug(
                    "Updated device %s: salt=%s lbs (%s%%), capacity=%s%%, status=%s",
                    device_id,
                    normalized.get("salt_lbs"),
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
