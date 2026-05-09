"""Sensor platform for Rainsoft integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
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
    """Set up Rainsoft sensors from config entry."""
    coordinator: RainsoftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    for device_id in coordinator.data:
        entities.extend(
            [
                RainsoftSaltLevelSensor(coordinator, device_id),
                RainsoftSalt28DaySensor(coordinator, device_id),
                RainsoftCapacitySensor(coordinator, device_id),
                RainsoftDailyWaterUseSensor(coordinator, device_id),
                RainsoftWater28DaySensor(coordinator, device_id),
                RainsoftFlowSinceLastRegenSensor(coordinator, device_id),
                RainsoftLifetimeFlowSensor(coordinator, device_id),
                RainsoftRegens28DaySensor(coordinator, device_id),
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
        """Initialize sensor."""
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
    """Salt level in pounds."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize salt level sensor."""
        super().__init__(coordinator, device_id, "salt_level", "Salt Level")
        self._attr_native_unit_of_measurement = UnitOfMass.POUNDS
        self._attr_icon = "mdi:shaker"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("salt_lbs")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "salt_pct": data.get("salt_level"),
            "max_salt_lbs": data.get("max_salt"),
            "device_id": self._device_id,
        }


class RainsoftSalt28DaySensor(RainsoftSensor):
    """Salt used in last 28 days."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize 28-day salt sensor."""
        super().__init__(coordinator, device_id, "salt_28day", "Salt Used (28 Days)")
        self._attr_native_unit_of_measurement = UnitOfMass.POUNDS
        self._attr_icon = "mdi:shaker"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("salt_28day")


class RainsoftCapacitySensor(RainsoftSensor):
    """Softening capacity remaining before next regeneration."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize capacity sensor."""
        super().__init__(coordinator, device_id, "capacity_remaining", "Capacity Remaining")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("capacity_remaining")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self._get_device_data()
        return {
            "flow_since_last_regen": data.get("flow_since_last_regen"),
            "device_id": self._device_id,
        }


class RainsoftDailyWaterUseSensor(RainsoftSensor):
    """Daily water use in gallons."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize daily water use sensor."""
        super().__init__(coordinator, device_id, "daily_water_use", "Daily Water Use")
        self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS
        self._attr_icon = "mdi:water"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("daily_water_use")


class RainsoftWater28DaySensor(RainsoftSensor):
    """Water used in last 28 days."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize 28-day water use sensor."""
        super().__init__(coordinator, device_id, "water_28day", "Water Use (28 Days)")
        self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS
        self._attr_icon = "mdi:water-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("water_28day")


class RainsoftFlowSinceLastRegenSensor(RainsoftSensor):
    """Gallons used since last regeneration."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize flow since regen sensor."""
        super().__init__(coordinator, device_id, "flow_since_last_regen", "Flow Since Last Regen")
        self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS
        self._attr_icon = "mdi:water-sync"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("flow_since_last_regen")


class RainsoftLifetimeFlowSensor(RainsoftSensor):
    """Total lifetime water flow in gallons."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize lifetime flow sensor."""
        super().__init__(coordinator, device_id, "lifetime_flow", "Lifetime Flow")
        self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("lifetime_flow")


class RainsoftRegens28DaySensor(RainsoftSensor):
    """Regeneration cycles in last 28 days."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize regens 28-day sensor."""
        super().__init__(coordinator, device_id, "regens_28day", "Regenerations (28 Days)")
        self._attr_icon = "mdi:refresh-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sensor value."""
        return self._get_device_data().get("regens_28day")


class RainsoftLastRegenerationSensor(RainsoftSensor):
    """Last regeneration datetime sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize last regeneration sensor."""
        super().__init__(
            coordinator, device_id, "last_regeneration", "Last Regeneration"
        )
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> datetime | None:
        """Return sensor value."""
        data = self._get_device_data()
        date_str = data.get("last_regeneration")
        return self._parse_dt(date_str)

    @staticmethod
    def _parse_dt(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt_util.as_local(dt)
            return dt
        except (ValueError, AttributeError) as err:
            _LOGGER.warning("Could not parse datetime '%s': %s", date_str, err)
            return None


class RainsoftNextRegenerationSensor(RainsoftSensor):
    """Next regeneration datetime sensor."""

    def __init__(
        self, coordinator: RainsoftDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize next regeneration sensor."""
        super().__init__(
            coordinator, device_id, "next_regeneration", "Next Regeneration"
        )
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> datetime | None:
        """Return sensor value."""
        data = self._get_device_data()
        date_str = data.get("next_regeneration")
        return RainsoftLastRegenerationSensor._parse_dt(date_str)
