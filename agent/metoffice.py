
import asyncio
import json
import os
from typing import Any

import boto3
import httpx2
from dotenv import load_dotenv

load_dotenv()


# --------------------------------------------------
# 1. Met Office API configuration
# --------------------------------------------------

METOFFICE_URL = (
    "https://data.hub.api.metoffice.gov.uk"
    "/sitespecific/v0/point/hourly"
)

DATA_SOURCE = "BD1"


# --------------------------------------------------
# 2. Official Met Office significant weather codes
# --------------------------------------------------

WEATHER_CODES = {
    -1: "Trace rain",
    0: "Clear night",
    1: "Sunny day",
    2: "Partly cloudy (night)",
    3: "Partly cloudy (day)",
    5: "Mist",
    6: "Fog",
    7: "Cloudy",
    8: "Overcast",
    9: "Light rain shower (night)",
    10: "Light rain shower (day)",
    11: "Drizzle",
    12: "Light rain",
    13: "Heavy rain shower (night)",
    14: "Heavy rain shower (day)",
    15: "Heavy rain",
    16: "Sleet shower (night)",
    17: "Sleet shower (day)",
    18: "Sleet",
    19: "Hail shower (night)",
    20: "Hail shower (day)",
    21: "Hail",
    22: "Light snow shower (night)",
    23: "Light snow shower (day)",
    24: "Light snow",
    25: "Heavy snow shower (night)",
    26: "Heavy snow shower (day)",
    27: "Heavy snow",
    28: "Thunder shower (night)",
    29: "Thunder shower (day)",
    30: "Thunder",
}


# --------------------------------------------------
# 3. Retrieve Met Office API key
# --------------------------------------------------

def get_metoffice_api_key() -> str:
    """
    Retrieve API key from:
    1. Local environment for development.
    2. AWS Secrets Manager for AgentCore.
    """

    local_key = os.getenv("METOFFICE_API_KEY")

    if local_key:
        return local_key

    secret_arn = os.getenv("METOFFICE_SECRET_ARN")

    if not secret_arn:
        raise RuntimeError(
            "METOFFICE_SECRET_ARN is not configured"
        )

    client = boto3.client("secretsmanager")

    response = client.get_secret_value(
        SecretId=secret_arn
    )

    secret = json.loads(response["SecretString"])

    api_key = secret.get("METOFFICE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "METOFFICE_API_KEY not found in secret"
        )

    return api_key


# --------------------------------------------------
# 4. Call Met Office Global Spot hourly API
# --------------------------------------------------

async def get_uk_weather(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """Retrieve the raw hourly weather forecast."""

    if not (-90 <= latitude <= 90):
        raise ValueError("Invalid latitude")

    if not (-180 <= longitude <= 180):
        raise ValueError("Invalid longitude")

    api_key = await asyncio.to_thread(
        get_metoffice_api_key
    )

    headers = {
        "apikey": api_key,
        "Accept": "application/json",
    }

    params = {
        "dataSource": DATA_SOURCE,
        "latitude": latitude,
        "longitude": longitude,
        "includeLocationName": "true",
    }

    async with httpx2.AsyncClient(
        timeout=30.0
    ) as client:

        response = await client.get(
            METOFFICE_URL,
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        return response.json()


# --------------------------------------------------
# 5. Convert significant weather code to text
# --------------------------------------------------

def get_weather_condition(code: Any) -> str:
    """Return a readable weather condition."""

    if code is None:
        return "Unknown"

    try:
        code = int(code)
    except (TypeError, ValueError):
        return "Unknown"

    return WEATHER_CODES.get(code, "Unknown")


# --------------------------------------------------
# 6. Format hourly weather forecast
# --------------------------------------------------

def format_uk_forecast(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert raw Met Office data into structured
    weather information for our MCP server.
    """

    features = data.get("features") or []

    if not features:
        raise ValueError(
            "Met Office returned no forecast features"
        )

    properties = features[0].get("properties") or {}

    location = properties.get("location") or {}

    # Maximum 48 hourly records.
    hours = properties.get("timeSeries", [])[:48]

    forecast = []

    for hour in hours:

        raw_code = hour.get(
            "significantWeatherCode"
        )

        try:
            weather_code = (
                int(raw_code)
                if raw_code is not None
                else None
            )
        except (TypeError, ValueError):
            weather_code = None

        hourly_forecast = {

            # Forecast time in UTC.
            "time": hour.get("time"),

            # Temperature.
            "temperature_c": hour.get(
                "screenTemperature"
            ),

            "feels_like_c": hour.get(
                "feelsLikeTemperature"
            ),

            # Weather conditions.
            "weather_code": weather_code,

            "condition": get_weather_condition(
                weather_code
            ),

            # Precipitation.
            "rain_probability_percent": hour.get(
                "probOfPrecipitation"
            ),

            "rainfall_mm": hour.get(
                "totalPrecipAmount"
            ),

            "precipitation_rate_mm_per_hour": (
                hour.get("precipitationRate")
            ),

            # Wind.
            "wind_speed_mps": hour.get(
                "windSpeed10m"
            ),

            "wind_gust_mps": hour.get(
                "windGustSpeed10m"
            ),

            "wind_direction_degrees": hour.get(
                "windDirectionFrom10m"
            ),

            # Humidity.
            "humidity_percent": hour.get(
                "screenRelativeHumidity"
            ),

            # Visibility.
            "visibility_m": hour.get(
                "visibility"
            ),

            # Atmospheric pressure.
            "pressure_pa": hour.get(
                "mslp"
            ),

            # UV index.
            "uv_index": hour.get(
                "uvIndex"
            ),
        }

        forecast.append(hourly_forecast)

    return {
        "location": location.get(
            "name",
            "Unknown"
        ),

        "model_run": properties.get(
            "modelRunDate"
        ),

        "forecast": forecast,
    }


# --------------------------------------------------
# 7. Local test
# --------------------------------------------------

async def main():

    # Exeter coordinates.
    latitude = 50.7184
    longitude = -3.5339

    print("Fetching Met Office forecast...")

    raw_data = await get_uk_weather(
        latitude,
        longitude,
    )

    result = format_uk_forecast(raw_data)

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    print(
        "Total forecast hours:",
        len(result["forecast"])
    )


if __name__ == "__main__":
    asyncio.run(main())
