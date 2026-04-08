"""Constants for the PetSafe Smart Feed integration."""

from homeassistant.const import Platform

DOMAIN = "petsafe_smartfeed"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

# Config keys
CONF_EMAIL = "email"
CONF_ID_TOKEN = "id_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN = "access_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"

# API constants
COGNITO_CLIENT_ID = "18hpp04puqmgf5nc6o474lcp2g"
COGNITO_REGION = "us-east-1"
COGNITO_ENDPOINT = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
API_BASE_URL = "https://platform.cloud.petsafe.net/smart-feed/"

# Rate limiting
MIN_API_INTERVAL = 300  # 5 minutes in seconds

# Food status mapping (API value -> display string)
FOOD_STATUS_MAP = {0: "Full", 1: "Low", 2: "Empty"}
FOOD_STATUS_OPTIONS = list(FOOD_STATUS_MAP.values())

# Battery voltage constants (from Techzune library)
BATTERY_VOLTAGE_MIN = 22755
BATTERY_VOLTAGE_MAX = 29100
