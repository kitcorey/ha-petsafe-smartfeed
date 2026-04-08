# PetSafe Smart Feed v2 - Home Assistant Integration

Custom Home Assistant integration for the PetSafe Smart Feed v2 automatic pet feeder.

## Features

- **Battery Level** sensor (0-100%, raw voltage in attributes)
- **Food Level** sensor (Full / Low / Empty)
- **Last Seen** sensor (when the feeder last connected to the cloud)
- **Settings Synced** binary sensor (detects when settings haven't reached the feeder)
- **Slow Feed** switch
- **Paused** switch (pause/resume scheduled feedings)
- **Child Lock** switch
- **Feed service** (`petsafe_smartfeed.feed`) to dispense food on demand

## Installation

### Manual

1. Copy `custom_components/petsafe_smartfeed/` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings > Devices & Services > Add Integration** and search for "PetSafe Smart Feed"

### Setup

The integration uses PetSafe's passwordless email authentication:

1. Enter the email address associated with your PetSafe account
2. Check your email for a verification code from PetSafe
3. Enter the code in Home Assistant

The integration will discover all feeders on your account automatically.

## Rate Limiting

The PetSafe API is undocumented and community-reverse-engineered. This integration polls every 5 minutes to be conservative:

- Data is polled every 5 minutes via the DataUpdateCoordinator
- Switch toggles and feed commands use optimistic local state updates to provide instant UI feedback

## Services

### `petsafe_smartfeed.feed`

Dispense food from a feeder.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_id` | string | required | The feeder device |
| `amount` | int (1-8) | 1 | Portions in 1/8 cup increments |
| `slow_feed` | bool | false | Dispense food slowly |

Example: to create a "snack" button in the UI, add a Helpers > Button and create an automation that calls the feed service when pressed.

## Example Automations

See `example_automations/` for ready-to-use automation YAML for:

- **Battery low alert** - notifies when battery drops below 20%
- **Food low alert** - notifies when the food level changes to Low or Empty
- **Connection lost alert** - notifies when the feeder hasn't connected in 24 hours
- **Settings not synced alert** - notifies when settings changes haven't reached the feeder

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
