"""Rainsoft API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from .const import (
    API_BASE_URL,
    API_HEADER_ACCEPT,
    API_HEADER_AUTH,
    API_HEADER_ORIGIN,
    API_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class RainsoftApiError(Exception):
    """Base exception for Rainsoft API errors."""


class RainsoftAuthError(RainsoftApiError):
    """Authentication error."""


class RainsoftConnectionError(RainsoftApiError):
    """Connection error."""


class RainsoftApiClient:
    """Rainsoft API client."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        """Initialize API client.

        Args:
            session: aiohttp ClientSession
            email: Rainsoft account email
            password: Rainsoft account password
        """
        self._session = session
        self._email = email.lower().strip()  # Normalize email
        self._password = password
        self._token: str | None = None
        self._customer_id: str | None = None
        self._base_url = API_BASE_URL

    async def authenticate(self) -> bool:
        """Authenticate and get token.

        Returns:
            True if authentication successful

        Raises:
            RainsoftAuthError: If authentication fails
            RainsoftConnectionError: If connection fails
        """
        _LOGGER.debug("Authenticating with Rainsoft API")

        try:
            data = aiohttp.FormData()
            data.add_field("email", self._email)
            data.add_field("password", self._password)

            response = await self._request(
                "POST",
                "/login",
                data=data,
                authenticated=False,
            )

            if not response or "authentication_token" not in response:
                raise RainsoftAuthError("Invalid response from login endpoint")

            self._token = response["authentication_token"]
            _LOGGER.debug("Authentication successful")
            return True

        except RainsoftConnectionError:
            raise
        except RainsoftAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during authentication: %s", err)
            raise RainsoftAuthError(f"Authentication failed: {err}") from err

    async def get_customer_id(self) -> str:
        """Get customer ID after authentication.

        Returns:
            Customer ID string

        Raises:
            RainsoftAuthError: If not authenticated
            RainsoftConnectionError: If connection fails
        """
        if not self._token:
            raise RainsoftAuthError("Not authenticated")

        _LOGGER.debug("Fetching customer ID")

        response = await self._request("GET", "/customer")

        if not response or "id" not in response:
            raise RainsoftApiError("Invalid response from customer endpoint")

        self._customer_id = str(response["id"])
        _LOGGER.debug("Customer ID: %s", self._customer_id)
        return self._customer_id

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices for customer.

        Returns:
            List of device dictionaries

        Raises:
            RainsoftAuthError: If not authenticated
            RainsoftConnectionError: If connection fails
        """
        if not self._customer_id:
            await self.get_customer_id()

        _LOGGER.debug("Fetching devices for customer %s", self._customer_id)

        response = await self._request("GET", f"/locations/{self._customer_id}")

        if not response or "locationListData" not in response:
            raise RainsoftApiError("Invalid response from locations endpoint")

        # Extract devices from locations
        devices = []
        for location in response["locationListData"]:
            if "devices" in location:
                for device in location["devices"]:
                    # Add location info to device
                    device["location_id"] = location.get("id")
                    device["location_name"] = location.get("name")
                    devices.append(device)

        _LOGGER.debug("Found %d device(s)", len(devices))
        return devices

    async def get_device_status(self, device_id: str) -> dict[str, Any]:
        """Get current status for a device.

        Args:
            device_id: Device ID

        Returns:
            Device status dictionary

        Raises:
            RainsoftAuthError: If not authenticated
            RainsoftConnectionError: If connection fails
        """
        _LOGGER.debug("Fetching status for device %s", device_id)

        response = await self._request("GET", f"/device/{device_id}")

        if not response or "device" not in response:
            raise RainsoftApiError("Invalid response from device endpoint")

        device_data = response["device"]

        # Parse and normalize the data
        return self._parse_device_data(device_data)

    async def force_update(self) -> bool:
        """Request fresh data from device.

        Returns:
            True if successful

        Raises:
            RainsoftConnectionError: If connection fails
        """
        _LOGGER.debug("Requesting force update")

        try:
            await self._request("GET", "/forceupdate")
            return True
        except Exception as err:
            _LOGGER.warning("Force update failed: %s", err)
            return False

    def _parse_device_data(self, device_data: dict[str, Any]) -> dict[str, Any]:
        """Parse and normalize device data.

        Args:
            device_data: Raw device data from API

        Returns:
            Normalized device data dictionary
        """
        # Extract key fields with safe defaults
        parsed = {
            "device_id": device_data.get("id"),
            "device_name": device_data.get("name", "Rainsoft Water Softener"),
            "model": device_data.get("model"),
            "serial_number": device_data.get("serial_number"),
            "firmware_version": device_data.get("firmware_version"),

            # Salt and capacity
            "salt_level": self._safe_int(device_data.get("salt_level")),
            "capacity_remaining": self._safe_int(device_data.get("capacity_remaining")),

            # System status
            "system_status": device_data.get("system_status_name", "unknown"),

            # Regeneration
            "last_regeneration": device_data.get("last_regeneration_date"),
            "next_regeneration": device_data.get("next_regeneration_time"),

            # Additional info
            "dealer_name": device_data.get("dealer_name"),
            "dealer_phone": device_data.get("dealer_phone"),
            "dealer_email": device_data.get("dealer_email"),
        }

        # Determine if regeneration is active
        system_status = parsed["system_status"].lower() if parsed["system_status"] else ""
        parsed["regeneration_active"] = "regenerat" in system_status

        return parsed

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Integer value or default
        """
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            _LOGGER.warning("Could not convert %s to int, using default %d", value, default)
            return default

    async def _request(
        self,
        method: str,
        endpoint: str,
        authenticated: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """Make authenticated request with auto token refresh.

        Args:
            method: HTTP method
            endpoint: API endpoint
            authenticated: Whether to include auth token
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Response JSON as dictionary

        Raises:
            RainsoftAuthError: If authentication fails
            RainsoftConnectionError: If connection fails
            RainsoftApiError: For other API errors
        """
        url = f"{self._base_url}{endpoint}"

        # Set up headers
        headers = kwargs.pop("headers", {})
        headers[aiohttp.hdrs.ACCEPT] = API_HEADER_ACCEPT
        headers[aiohttp.hdrs.ORIGIN] = API_HEADER_ORIGIN

        if authenticated and self._token:
            headers[API_HEADER_AUTH] = self._token

        # Set timeout
        timeout = ClientTimeout(total=API_TIMEOUT)

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
                **kwargs,
            ) as response:
                response_text = await response.text()

                _LOGGER.debug(
                    "API request: %s %s - Status: %d",
                    method,
                    endpoint,
                    response.status,
                )

                # Handle 400 error by re-authenticating
                if response.status == 400 and authenticated:
                    _LOGGER.info("Received 400 error, attempting to re-authenticate")
                    await self.authenticate()

                    # Retry request once with new token
                    headers[API_HEADER_AUTH] = self._token
                    async with self._session.request(
                        method,
                        url,
                        headers=headers,
                        timeout=timeout,
                        **kwargs,
                    ) as retry_response:
                        retry_text = await retry_response.text()

                        if retry_response.status != 200:
                            raise RainsoftAuthError(
                                f"Authentication retry failed with status {retry_response.status}"
                            )

                        try:
                            return await retry_response.json()
                        except Exception as err:
                            _LOGGER.error("Failed to parse JSON response: %s", retry_text)
                            raise RainsoftApiError(f"Invalid JSON response: {err}") from err

                # Handle error status codes
                if response.status == 401:
                    raise RainsoftAuthError("Unauthorized - invalid credentials")
                elif response.status == 404:
                    raise RainsoftApiError(f"Endpoint not found: {endpoint}")
                elif response.status >= 500:
                    raise RainsoftConnectionError(
                        f"Server error: {response.status}"
                    )
                elif response.status != 200:
                    raise RainsoftApiError(
                        f"API request failed with status {response.status}"
                    )

                # Parse JSON response
                try:
                    return await response.json()
                except Exception as err:
                    _LOGGER.error("Failed to parse JSON response: %s", response_text)
                    raise RainsoftApiError(f"Invalid JSON response: {err}") from err

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            raise RainsoftConnectionError(f"Connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Request timeout after %d seconds", API_TIMEOUT)
            raise RainsoftConnectionError("Request timeout") from err
