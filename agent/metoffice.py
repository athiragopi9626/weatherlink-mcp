
import os
import asyncio
import httpx2
from dotenv import load_dotenv
import json
import boto3

load_dotenv()

def get_metoffice_api_key() -> str:
    """Get the Met Office API key from local environment or AWS Secrets Manager."""

    # Local development: use the key from .env.
    local_key = os.getenv("METOFFICE_API_KEY")
    if local_key:
        return local_key

    # AWS AgentCore: use the secret ARN passed by Terraform.
    secret_arn = os.getenv("METOFFICE_SECRET_ARN")
    if not secret_arn:
        raise RuntimeError("METOFFICE_SECRET_ARN is not configured")

    # Boto3 uses the AgentCore execution role credentials.
    client = boto3.client("secretsmanager")

    response = client.get_secret_value(SecretId=secret_arn)

    # Read the JSON key/value secret.
    secret = json.loads(response["SecretString"])
    api_key = secret.get("METOFFICE_API_KEY")

    if not api_key:
        raise RuntimeError("METOFFICE_API_KEY not found in secret")

    return api_key

URL = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/hourly"


async def get_uk_weather(latitude: float, longitude: float):
    # Retrieve API key from .env locally or AWS Secrets Manager.
    api_key = await asyncio.to_thread(get_metoffice_api_key)

    # Pass the retrieved API key to the Met Office API.
    headers = {
        "apikey": api_key
    }

    params = {
        "dataSource": "BD1",
        "latitude": latitude,
        "longitude": longitude,
        "includeLocationName": "true",
    }

    async with httpx2.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            URL,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()



def format_uk_forecast(data: dict) -> dict:
    # The Met Office API returns a FeatureCollection.
    # We access the first location's forecast properties.
    properties = data["features"][0]["properties"]

    # timeSeries contains hourly weather forecasts.
    # [:6] selects only the first 6 hours to reduce MCP output size.
    hours = properties["timeSeries"][:6]

    # Empty list to store our simplified hourly forecasts.
    forecast = []

    # Process each hourly forecast.
    for hour in hours:
        forecast.append({
            # Forecast timestamp (UTC).
            "time": hour["time"],

            # Air temperature in degrees Celsius.
            "temperature_c": hour.get("screenTemperature"),

            # Temperature as it feels to a person (Celsius).
            "feels_like_c": hour.get("feelsLikeTemperature"),

            # Wind speed measured at 10 metres above ground (m/s).
            "wind_speed_mps": hour.get("windSpeed10m"),

            # Wind gust speed in metres per second.
            "wind_gust_mps": hour.get("windGustSpeed10m"),

            # Probability of precipitation, as a percentage.
            "rain_probability_percent": hour.get("probOfPrecipitation"),

            # Total precipitation during the previous hour (mm).
            "rainfall_mm": hour.get("totalPrecipAmount"),
        })

    # Return only the information our AI agent needs.
    return {
        "location": properties["location"]["name"],

        # When the weather prediction model was run.
        "model_run": properties["modelRunDate"],

        # Our simplified list of hourly forecasts.
        "forecast": forecast,
    }


async def main():
    data = await get_uk_weather(50.7184, -3.5339)
    print(data)


if __name__ == "__main__":
    asyncio.run(main())
