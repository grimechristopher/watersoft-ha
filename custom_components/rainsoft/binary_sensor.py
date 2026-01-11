"""Binary sensor platform for Rainsoft integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SALT_LOW_THRESHOLD
from .coordinator import RainsoftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rainsoft binary sensors from config entry.

    Args:
        hass: HomeAssistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: RainsoftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Create binary sensors for each device
    for device_id in coordinator.data:
        entities.extend(
            [
                RainsoftSystemAlertSensor(coordinator, device_id),
                RainsoftRegenerationSensor(coordinator, device_id),
                RainsoftSaltLowSensor(coordinator, device_id),
            ]
        )

    _LOGGER.debug("Adding %d binary sensor entities", len(entities))
    async_add_entities(entities)


class RainsoftBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base Rainsoft binary sensor."""

    def __init__(
        self,
        coordinator: RainsoftDataUpdateCoordinator,
        device_id: str,
        sensor_key: str,
        name_suffix: str,
    ) -> None:
        """Initialize binary sensor.

        Args:
            coordinator: Data coordinator
            device_id: Device ID
            sensor_key: Key for sensor
            name_suffix: Suffix for entity name
        """
        super().__init__(coordinator)
        self._device_id = device_id
        self._sensor_key = sensor_key
        self._name_suffix = name_suffix
        self._attr_unique_id = f"{device_id}_{sensor_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        device = self.coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.get("device_name", "Rainsoft Water Softener"),
            manufacturer="Rainsoft",
            model=device.get("model"),
            sw_version=device.get("firmware_version"),
        )

    @property
    def name(self) -> str:
        """Return entity name."""
        device = self.coordinator.data.get(self._device_id, {})
        device_name = device.get("device_name", "Rainsoft Water Softener")
        return f"{device_name} {self._name_suffix}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._device_id in self.coordinator.data
        )

    def _get_device_data(self) -> dict[str, Any]:
        """Get device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})


class RainsoftSystemAlertSensor(RainsoftBinarySensor):
    """System alert binary sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize system alert sensor."""
        super().__init__(coordinator, device_id, "system_alert", "Alert")
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if alert is active.

        Any status other than 'normal' is considered an alert.
        """
        data = self._get_device_data()
        status = data.get("system_status", "normal")

        if not status:
            return False

        # Any status other than "normal" is an alert
        return status.lower() != "normal"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "system_status": data.get("system_status"),
            "device_id": self._device_id,
        }


class RainsoftRegenerationSensor(RainsoftBinarySensor):
    """Regeneration active binary sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize regeneration sensor."""
        super().__init__(coordinator, device_id, "regeneration_active", "Regenerating")
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        """Return True if regeneration is active."""
        data = self._get_device_data()
        return data.get("regeneration_active", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "last_regeneration": data.get("last_regeneration"),
            "next_regeneration": data.get("next_regeneration"),
            "device_id": self._device_id,
        }


class RainsoftSaltLowSensor(RainsoftBinarySensor):
    """Salt level low binary sensor (using battery metaphor)."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize salt low sensor."""
        super().__init__(coordinator, device_id, "salt_low", "Salt Low")
        self._attr_device_class = BinarySensorDeviceClass.BATTERY

    @property
    def is_on(self) -> bool:
        """Return True if salt level is low (<20%).

        Following the homebridge plugin pattern, we use the battery
        device class to represent salt level, where ON means low battery
        (low salt).
        """
        data = self._get_device_data()
        salt_level = data.get("salt_level", 100)

        # Consider salt low if below threshold
        return salt_level < SALT_LOW_THRESHOLD

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "salt_level": data.get("salt_level"),
            "threshold": SALT_LOW_THRESHOLD,
            "device_id": self._device_id,
        }
