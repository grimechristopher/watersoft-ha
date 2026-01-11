"""The Rainsoft integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RainsoftApiClient, RainsoftApiError, RainsoftAuthError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import RainsoftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rainsoft from a config entry.

    Args:
        hass: HomeAssistant instance
        entry: Config entry

    Returns:
        True if setup successful

    Raises:
        ConfigEntryAuthFailed: If authentication fails
        ConfigEntryNotReady: If setup should be retried
    """
    _LOGGER.debug("Setting up Rainsoft integration")

    # Get credentials from config entry
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    # Get scan interval from options (or use default)
    scan_interval_hours = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(hours=scan_interval_hours)

    _LOGGER.debug(
        "Scan interval: %d hours (%s)", scan_interval_hours, scan_interval
    )

    # Create API client
    session = async_get_clientsession(hass)
    api = RainsoftApiClient(session, email, password)

    # Authenticate
    try:
        await api.authenticate()
        await api.get_customer_id()
        _LOGGER.info("Successfully authenticated with Rainsoft API")

    except RainsoftAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise ConfigEntryAuthFailed("Authentication failed") from err

    except RainsoftApiError as err:
        _LOGGER.error("API error during setup: %s", err)
        raise ConfigEntryNotReady(f"API error: {err}") from err

    # Create coordinator
    coordinator = RainsoftDataUpdateCoordinator(hass, api, scan_interval)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        _LOGGER.error("Error fetching initial data: %s", err)
        raise ConfigEntryNotReady(f"Error fetching data: {err}") from err

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    _LOGGER.info(
        "Rainsoft integration setup complete with %d device(s)",
        len(coordinator.devices),
    )

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup options listener
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: HomeAssistant instance
        entry: Config entry

    Returns:
        True if unload successful
    """
    _LOGGER.debug("Unloading Rainsoft integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove coordinator from hass.data if unload successful
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Rainsoft integration unloaded successfully")

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: HomeAssistant instance
        entry: Config entry
    """
    _LOGGER.debug("Options updated, reloading Rainsoft integration")
    await hass.config_entries.async_reload(entry.entry_id)
