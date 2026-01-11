# Rainsoft Water Softener Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Monitor your Rainsoft water softener system in Home Assistant using the Rainsoft Remind app API.

## Features

- **Salt Level Monitoring**: Track salt percentage with low salt alerts
- **Water Capacity Tracking**: Monitor remaining softened water capacity
- **Regeneration Status**: View last regeneration date and next scheduled regeneration
- **System Alerts**: Get notified of system problems or maintenance needs
- **Cloud-based**: Works anywhere with internet access
- **UI Configuration**: Easy setup through Home Assistant UI
- **Automatic Updates**: Configurable polling interval (1-4 hours)

## Requirements

- Home Assistant 2024.1.0 or newer
- A Rainsoft water softener with Rainsoft Remind app access
- Valid Rainsoft Remind app credentials (email and password)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the **three dots** in the top right corner
4. Select **Custom repositories**
5. Add this repository URL: `https://github.com/yourusername/watersoft-ha`
6. Select **Integration** as the category
7. Click **Install**
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/rainsoft` directory to your Home Assistant `config/custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Rainsoft**
4. Enter your Rainsoft Remind app credentials:
   - **Email**: Your Rainsoft account email
   - **Password**: Your Rainsoft account password
5. Click **Submit**
6. (Optional) Configure the update interval in integration options (default: 2 hours)

### Options

After setup, you can configure the following options:

- **Update Interval**: How often to poll the API (1-4 hours, default: 2 hours)
  - Navigate to the integration and click **Configure**
  - Adjust the interval based on your preference
  - Lower intervals provide more frequent updates but may increase API load

## Entities

The integration creates 7 entities per water softener device:

### Sensors

| Entity | Description | Unit | Device Class |
|--------|-------------|------|--------------|
| **Salt Level** | Current salt percentage | % | - |
| **Capacity** | Remaining water softening capacity | % | - |
| **Last Regeneration** | Date of last regeneration cycle | - | Date |
| **Next Regeneration** | Scheduled next regeneration date | - | Date |

### Binary Sensors

| Entity | Description | Device Class | States |
|--------|-------------|--------------|--------|
| **Alert** | System problem or maintenance alert | Problem | ON = Alert, OFF = Normal |
| **Regenerating** | Active regeneration cycle | Running | ON = Regenerating, OFF = Idle |
| **Salt Low** | Low salt warning | Battery | ON = Salt Low (<20%), OFF = OK |

## Automations

Example automations you can create:

### Low Salt Alert

```yaml
automation:
  - alias: "Rainsoft - Low Salt Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.rainsoft_water_softener_salt_low
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Water Softener Alert"
          message: "Salt level is below 20%. Time to refill!"
```

### Regeneration Notification

```yaml
automation:
  - alias: "Rainsoft - Regeneration Started"
    trigger:
      - platform: state
        entity_id: binary_sensor.rainsoft_water_softener_regenerating
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Water Softener"
          message: "Regeneration cycle started"
```

### System Alert

```yaml
automation:
  - alias: "Rainsoft - System Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.rainsoft_water_softener_alert
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Water Softener Alert"
          message: "System problem detected. Check your water softener."
```

## Lovelace Card Example

```yaml
type: entities
title: Water Softener
entities:
  - entity: sensor.rainsoft_water_softener_salt_level
    name: Salt Level
  - entity: sensor.rainsoft_water_softener_capacity
    name: Capacity Remaining
  - entity: binary_sensor.rainsoft_water_softener_salt_low
    name: Salt Low
  - entity: binary_sensor.rainsoft_water_softener_alert
    name: System Alert
  - entity: binary_sensor.rainsoft_water_softener_regenerating
    name: Regenerating
  - entity: sensor.rainsoft_water_softener_last_regeneration
    name: Last Regeneration
  - entity: sensor.rainsoft_water_softener_next_regeneration
    name: Next Regeneration
```

## Troubleshooting

### Authentication Failed

- Verify your Rainsoft Remind app credentials are correct
- Try logging into the Rainsoft Remind mobile app to confirm your account is active
- Check if your account requires any actions (password reset, terms acceptance, etc.)

### Cannot Connect

- Check your Home Assistant internet connection
- Verify Rainsoft servers are accessible: `https://remind.rainsoft.com`
- Check Home Assistant logs for detailed error messages

### Sensors Show "Unavailable"

- Check if the integration is loaded: **Settings** → **Devices & Services** → **Rainsoft**
- Verify your credentials are still valid (may require re-authentication)
- Check the logs for connection or API errors
- Try reloading the integration

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.rainsoft: debug
```

Then restart Home Assistant and check the logs.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/watersoft-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/watersoft-ha/discussions)

## Credits

This integration is inspired by the [homebridge-rainsoft-remind](https://github.com/dash16/homebridge-rainsoft-remind) plugin.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to Rainsoft or Aquion, Inc. Use at your own risk.

## License

MIT License - see [LICENSE](LICENSE) file for details
