
from typing import Any

import httpx2
from mcp.server import MCPServer

# Create the MCP server
mcp = MCPServer("weatherlink")

# Weather API configuration
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weatherlink-mcp/1.0"


# Helper function to call the weather API
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make an HTTP request to the National Weather Service API."""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }

    async with httpx2.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers=headers,
                timeout=30.0,
            )

            response.raise_for_status()
            return response.json()

        except Exception:
            return None


# Format a weather alert
def format_alert(feature: dict) -> str:
    """Convert weather alert data into readable text."""

    props = feature["properties"]

    return f"""
Event: {props.get("event", "Unknown")}
Area: {props.get("areaDesc", "Unknown")}
Severity: {props.get("severity", "Unknown")}
Description: {props.get("description", "No description available")}
Instructions: {props.get("instruction", "No specific instructions provided")}
"""


# MCP Tool 1: Get weather alerts
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code, e.g. CA or NY.
    """

    url = f"{NWS_API_BASE}/alerts/active/area/{state}"

    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [
        format_alert(feature)
        for feature in data["features"]
    ]

    return "\n---\n".join(alerts)


# MCP Tool 2: Get weather forecast
@mcp.tool()
async def get_forecast(
    latitude: float,
    longitude: float,
) -> str:
    """Get weather forecast for a US location.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
    """

    # First API request: get forecast endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"

    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Extract the forecast URL
    forecast_url = points_data["properties"]["forecast"]

    # Second API request: get actual forecast
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Extract forecast periods
    periods = forecast_data["properties"]["periods"]

    forecasts = []

    # Process the first five periods
    for period in periods[:5]:
        forecast = f"""
{period["name"]}:
Temperature: {period["temperature"]}°{period["temperatureUnit"]}
Wind: {period["windSpeed"]} {period["windDirection"]}
Forecast: {period["detailedForecast"]}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)





# Import the Met Office API functions from the agent package.
from agent.metoffice import get_uk_weather, format_uk_forecast


# Register this function as an MCP tool.
# MCP clients (and later our LangGraph agent) can discover and call it.
@mcp.tool()
async def get_uk_forecast(latitude: float, longitude: float) -> dict:
    """
    Get a compact UK hourly forecast from the Met Office.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
    """

    # Step 1: Call the Met Office API and receive the full JSON response.
    data = await get_uk_weather(latitude, longitude)

    # Step 2: Extract the relevant weather fields.
    # This reduces the amount of data returned to the MCP client.
    return format_uk_forecast(data)



# Start the MCP server
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
