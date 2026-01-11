#!/usr/bin/env python3
"""Test script for Rainsoft API - Debug authentication and data fetching."""

import argparse
import json
import os
import sys
from typing import Any, Optional

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Missing dependencies. Install with:")
    print("  pip install -r requirements-test.txt")
    sys.exit(1)


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


# API Configuration
API_BASE_URL = "https://remind.rainsoft.com/api/remindapp/v2"
API_HEADERS = {
    "Accept": "application/json",
    "Origin": "ionic://localhost",
}
TIMEOUT = 30


def print_header(text: str) -> None:
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_json(data: Any, indent: int = 2) -> None:
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent))


def mask_token(token: str) -> str:
    """Mask token for display."""
    if len(token) <= 10:
        return "***"
    return token[:6] + "***"


class RainsoftApiTester:
    """Test the Rainsoft API endpoints."""

    def __init__(self, email: str, password: str):
        """Initialize tester with credentials."""
        self.email = email.lower().strip()
        self.password = password
        self.token: Optional[str] = None
        self.customer_id: Optional[str] = None
        self.session = requests.Session()

    def test_authentication(self) -> bool:
        """Test /login endpoint."""
        print_header("STEP 1: Authentication")

        url = f"{API_BASE_URL}/login"
        print(f"POST {url}")
        print(f"Headers: {API_HEADERS}")
        print(f"Data: email={self.email}, password=***")

        try:
            response = self.session.post(
                url,
                headers=API_HEADERS,
                data={"email": self.email, "password": self.password},
                timeout=TIMEOUT,
            )

            print(f"\nStatus: {response.status_code}")

            if response.status_code != 200:
                print_error(f"Authentication failed with status {response.status_code}")
                print(f"Response body: {response.text}")
                return False

            data = response.json()
            print("\nResponse JSON:")
            print_json(data)

            if "authentication_token" not in data:
                print_error("No 'authentication_token' in response")
                return False

            self.token = data["authentication_token"]
            print_success(f"Token obtained: {mask_token(self.token)}")
            return True

        except requests.exceptions.RequestException as err:
            print_error(f"Connection error: {err}")
            return False
        except json.JSONDecodeError as err:
            print_error(f"Invalid JSON response: {err}")
            print(f"Response text: {response.text}")
            return False

    def test_customer_id(self) -> bool:
        """Test /customer endpoint."""
        print_header("STEP 2: Get Customer ID")

        if not self.token:
            print_error("Not authenticated - skipping")
            return False

        url = f"{API_BASE_URL}/customer"
        headers = {**API_HEADERS, "X-Remind-Auth-Token": self.token}

        print(f"GET {url}")
        print(f"Headers: {{'X-Remind-Auth-Token': '{mask_token(self.token)}', ...}}")

        try:
            response = self.session.get(url, headers=headers, timeout=TIMEOUT)

            print(f"\nStatus: {response.status_code}")

            if response.status_code != 200:
                print_error(f"Request failed with status {response.status_code}")
                print(f"Response body: {response.text}")
                return False

            data = response.json()
            print("\nResponse JSON:")
            print_json(data)

            # Check for customer ID (returned at root level, not nested)
            if "id" not in data:
                print_error("No 'id' field in response")
                return False

            self.customer_id = str(data["id"])
            print_success(f"Customer ID: {self.customer_id}")
            return True

        except requests.exceptions.RequestException as err:
            print_error(f"Connection error: {err}")
            return False
        except json.JSONDecodeError as err:
            print_error(f"Invalid JSON response: {err}")
            print(f"Response text: {response.text}")
            return False

    def test_devices(self) -> list[dict[str, Any]]:
        """Test /locations endpoint."""
        print_header("STEP 3: Get Devices")

        if not self.token or not self.customer_id:
            print_error("Not authenticated or no customer ID - skipping")
            return []

        url = f"{API_BASE_URL}/locations/{self.customer_id}"
        headers = {**API_HEADERS, "X-Remind-Auth-Token": self.token}

        print(f"GET {url}")
        print(f"Headers: {{'X-Remind-Auth-Token': '{mask_token(self.token)}', ...}}")

        try:
            response = self.session.get(url, headers=headers, timeout=TIMEOUT)

            print(f"\nStatus: {response.status_code}")

            if response.status_code != 200:
                print_error(f"Request failed with status {response.status_code}")
                print(f"Response body: {response.text}")
                return []

            data = response.json()
            print("\nResponse JSON:")
            print_json(data)

            # Extract devices from locations (API uses locationListData)
            if "locationListData" not in data:
                print_error("No 'locationListData' field in response")
                return []

            devices = []
            for location in data["locationListData"]:
                if "devices" in location:
                    for device in location["devices"]:
                        device["location_id"] = location.get("id")
                        device["location_name"] = location.get("name")
                        devices.append(device)

            print_success(f"Found {len(devices)} device(s)")
            return devices

        except requests.exceptions.RequestException as err:
            print_error(f"Connection error: {err}")
            return []
        except json.JSONDecodeError as err:
            print_error(f"Invalid JSON response: {err}")
            print(f"Response text: {response.text}")
            return []

    def test_device_status(self, device_id: str, device_name: str) -> Optional[dict[str, Any]]:
        """Test /device endpoint."""
        print_header(f"STEP 4: Get Status for '{device_name}' (ID: {device_id})")

        if not self.token:
            print_error("Not authenticated - skipping")
            return None

        url = f"{API_BASE_URL}/device/{device_id}"
        headers = {**API_HEADERS, "X-Remind-Auth-Token": self.token}

        print(f"GET {url}")
        print(f"Headers: {{'X-Remind-Auth-Token': '{mask_token(self.token)}', ...}}")

        try:
            response = self.session.get(url, headers=headers, timeout=TIMEOUT)

            print(f"\nStatus: {response.status_code}")

            if response.status_code != 200:
                print_error(f"Request failed with status {response.status_code}")
                print(f"Response body: {response.text}")
                return None

            data = response.json()
            print("\nResponse JSON:")
            print_json(data)

            if "device" not in data:
                print_error("No 'device' field in response")
                return None

            device_data = data["device"]
            print_success("Device status retrieved successfully")
            return device_data

        except requests.exceptions.RequestException as err:
            print_error(f"Connection error: {err}")
            return None
        except json.JSONDecodeError as err:
            print_error(f"Invalid JSON response: {err}")
            print(f"Response text: {response.text}")
            return None

    def print_summary(self, devices_data: list[dict[str, Any]]) -> None:
        """Print summary of API test."""
        print_header("SUMMARY")

        # Expected fields by HA integration
        expected_fields = {
            "id", "name", "model", "serial_number", "firmware_version",
            "salt_level", "capacity_remaining", "system_status_name",
            "last_regeneration_date", "next_regeneration_time",
            "dealer_name", "dealer_phone", "dealer_email"
        }

        if self.token:
            print_success("Authentication: Success")
        else:
            print_error("Authentication: Failed")
            return

        if self.customer_id:
            print_success(f"Customer ID: {self.customer_id}")
        else:
            print_error("Customer ID: Not retrieved")
            return

        print_success(f"Devices found: {len(devices_data)}")

        # Check fields in device data
        if devices_data:
            print("\n" + Colors.BOLD + "Device Data Analysis:" + Colors.END)
            for i, device in enumerate(devices_data, 1):
                print(f"\nDevice {i}: {device.get('name', 'Unknown')}")

                actual_fields = set(device.keys())
                missing_fields = expected_fields - actual_fields
                extra_fields = actual_fields - expected_fields

                if missing_fields:
                    print_warning(f"Missing fields HA expects: {sorted(missing_fields)}")
                else:
                    print_success("All expected fields present")

                if extra_fields:
                    print(f"Additional fields: {sorted(extra_fields)}")

                # Check specific important fields
                print(f"\nKey values:")
                print(f"  - Salt Level: {device.get('salt_level', 'N/A')}")
                print(f"  - Capacity: {device.get('capacity_remaining', 'N/A')}")
                print(f"  - System Status: {device.get('system_status_name', 'N/A')}")
                print(f"  - Last Regen: {device.get('last_regeneration_date', 'N/A')}")
                print(f"  - Next Regen: {device.get('next_regeneration_time', 'N/A')}")


def main():
    """Main entry point."""
    # Load .env file if it exists
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Test Rainsoft API authentication and data fetching"
    )
    parser.add_argument(
        "--email",
        default=os.getenv("RAINSOFT_EMAIL"),
        help="Rainsoft account email (or set RAINSOFT_EMAIL env var)"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("RAINSOFT_PASSWORD"),
        help="Rainsoft account password (or set RAINSOFT_PASSWORD env var)"
    )

    args = parser.parse_args()

    if not args.email or not args.password:
        print_error("Email and password are required")
        print("\nUsage:")
        print("  python test_rainsoft_api.py --email your@email.com --password yourpassword")
        print("\nOr set environment variables:")
        print("  export RAINSOFT_EMAIL='your@email.com'")
        print("  export RAINSOFT_PASSWORD='yourpassword'")
        print("  python test_rainsoft_api.py")
        sys.exit(1)

    print(f"{Colors.BOLD}Rainsoft API Tester{Colors.END}")
    print(f"Testing with email: {args.email}\n")

    tester = RainsoftApiTester(args.email, args.password)

    # Test authentication
    if not tester.test_authentication():
        sys.exit(1)

    # Test customer ID
    if not tester.test_customer_id():
        sys.exit(2)

    # Test devices
    devices = tester.test_devices()

    # Test device status for each device
    devices_data = []
    for device in devices:
        device_id = device.get("id")
        device_name = device.get("name", "Unknown")
        if device_id:
            status = tester.test_device_status(str(device_id), device_name)
            if status:
                devices_data.append(status)

    # Print summary
    tester.print_summary(devices_data)

    print(f"\n{Colors.GREEN}{Colors.BOLD}All tests completed!{Colors.END}\n")


if __name__ == "__main__":
    main()
