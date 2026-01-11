"""Sensor platform for Rainsoft integration."""
from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RainsoftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rainsoft sensors from config entry.

    Args:
        hass: HomeAssistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: RainsoftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Create sensors for each device
    for device_id in coordinator.data:
        entities.extend(
            [
                RainsoftSaltLevelSensor(coordinator, device_id),
                RainsoftCapacitySensor(coordinator, device_id),
                RainsoftLastRegenerationSensor(coordinator, device_id),
                RainsoftNextRegenerationSensor(coordinator, device_id),
            ]
        )

    _LOGGER.debug("Adding %d sensor entities", len(entities))
    async_add_entities(entities)


class RainsoftSensor(CoordinatorEntity, SensorEntity):
    """Base Rainsoft sensor."""

    def __init__(
        self,
        coordinator: RainsoftDataUpdateCoordinator,
        device_id: str,
        sensor_key: str,
        name_suffix: str,
    ) -> None:
        """Initialize sensor.

        Args:
            coordinator: Data coordinator
            device_id: Device ID
            sensor_key: Key for sensor data
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


class RainsoftSaltLevelSensor(RainsoftSensor):
    """Salt level sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize salt level sensor."""
        super().__init__(coordinator, device_id, "salt_level", "Salt Level")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:shaker"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        data = self._get_device_data()
        return data.get("salt_level")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "device_id": self._device_id,
            "model": data.get("model"),
        }


class RainsoftCapacitySensor(RainsoftSensor):
    """Capacity remaining sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize capacity sensor."""
        super().__init__(coordinator, device_id, "capacity_remaining", "Capacity")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        data = self._get_device_data()
        return data.get("capacity_remaining")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "device_id": self._device_id,
            "model": data.get("model"),
        }


class RainsoftLastRegenerationSensor(RainsoftSensor):
    """Last regeneration date sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize last regeneration sensor."""
        super().__init__(
            coordinator, device_id, "last_regeneration", "Last Regeneration"
        )
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> date | None:
        """Return sensor value."""
        data = self._get_device_data()
        date_str = data.get("last_regeneration")

        if not date_str:
            return None

        try:
            # Try to parse as ISO date or datetime
            if "T" in date_str or " " in date_str:
                # Contains time component
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.date()
            else:
                # Date only
                return date.fromisoformat(date_str)
        except (ValueError, AttributeError) as err:
            _LOGGER.warning(
                "Could not parse last regeneration date '%s': %s", date_str, err
            )
            return None


class RainsoftNextRegenerationSensor(RainsoftSensor):
    """Next regeneration date sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize next regeneration sensor."""
        super().__init__(
            coordinator, device_id, "next_regeneration", "Next Regeneration"
        )
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> date | None:
        """Return sensor value."""
        data = self._get_device_data()
        date_str = data.get("next_regeneration")

        if not date_str:
            return None

        try:
            # Try to parse as ISO date or datetime
            if "T" in date_str or " " in date_str:
                # Contains time component
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.date()
            else:
                # Date only
                return date.fromisoformat(date_str)
        except (ValueError, AttributeError) as err:
            _LOGGER.warning(
                "Could not parse next regeneration date '%s': %s", date_str, err
            )
            return None
