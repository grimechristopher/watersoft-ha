"""Constants for Rainsoft integration."""

DOMAIN = "rainsoft"

# Config flow
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL = 2  # hours
MIN_SCAN_INTERVAL = 1  # hour
MAX_SCAN_INTERVAL = 4  # hours

# API
API_BASE_URL = "https://remind.rainsoft.com/api/remindapp/v2"
API_TIMEOUT = 30  # seconds

# API Headers
API_HEADER_ACCEPT = "application/json"
API_HEADER_ORIGIN = "ionic://localhost"
API_HEADER_AUTH = "X-Remind-Auth-Token"

# Sensor types
SENSOR_SALT_LEVEL = "salt_level"
SENSOR_SALT_LBS = "salt_lbs"
SENSOR_SALT_28DAY = "salt_28day"
SENSOR_CAPACITY = "capacity_remaining"
SENSOR_DAILY_WATER_USE = "daily_water_use"
SENSOR_WATER_28DAY = "water_28day"
SENSOR_FLOW_SINCE_REGEN = "flow_since_last_regen"
SENSOR_LIFETIME_FLOW = "lifetime_flow"
SENSOR_REGENS_28DAY = "regens_28day"
SENSOR_LAST_REGEN = "last_regeneration"
SENSOR_NEXT_REGEN = "next_regeneration"

# Binary sensor types
BINARY_SENSOR_ALERT = "system_alert"
BINARY_SENSOR_REGEN = "regeneration_active"
BINARY_SENSOR_SALT_LOW = "salt_low"

# Salt low threshold (percentage)
SALT_LOW_THRESHOLD = 20
