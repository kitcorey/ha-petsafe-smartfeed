"""Shared test fixtures for PetSafe Smart Feed tests."""

import pytest

# Sample API response for a feeder
MOCK_FEEDER_API_RESPONSE = {
    "thing_name": "smart_feed_abc123",
    "id": "feeder-id-001",
    "battery_voltage": "26000",
    "is_batteries_installed": True,
    "is_food_low": 0,
    "food_sensor_current": 100,
    "connection_status": 2,
    "connection_status_timestamp": "2026-04-07T12:00:00.000Z",
    "revision_desired": 5,
    "revision_reported": 5,
    "settings": {
        "friendly_name": "Kitchen Feeder",
        "slow_feed": False,
        "paused": False,
        "child_lock": False,
        "pet_type": "cat",
    },
}

MOCK_FEEDER_LOW_BATTERY = {
    **MOCK_FEEDER_API_RESPONSE,
    "thing_name": "smart_feed_low_bat",
    "battery_voltage": "23000",
    "is_food_low": 1,
    "settings": {
        **MOCK_FEEDER_API_RESPONSE["settings"],
        "friendly_name": "Low Battery Feeder",
    },
}

MOCK_COGNITO_INITIATE_AUTH_RESPONSE = {
    "ChallengeName": "CUSTOM_CHALLENGE",
    "Session": "mock-session-token",
    "ChallengeParameters": {"USERNAME": "user@example.com"},
}

MOCK_COGNITO_AUTH_RESULT = {
    "AuthenticationResult": {
        "IdToken": "mock-id-token",
        "AccessToken": "mock-access-token",
        "RefreshToken": "mock-refresh-token",
        "ExpiresIn": 3600,
    }
}

MOCK_COGNITO_REFRESH_RESULT = {
    "AuthenticationResult": {
        "IdToken": "mock-id-token-refreshed",
        "AccessToken": "mock-access-token-refreshed",
        "ExpiresIn": 3600,
    }
}

MOCK_CONFIG_ENTRY_DATA = {
    "email": "user@example.com",
    "id_token": "mock-id-token",
    "refresh_token": "mock-refresh-token",
    "access_token": "mock-access-token",
    "token_expires_at": 0,
}
