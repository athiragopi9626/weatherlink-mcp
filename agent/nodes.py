
import json
import os

from langchain.mcp import MCPAdapter
from fastmcp import Client

from agent.mcp_auth import get_mcp_access_token


# --------------------------------------------------
# 1. Helper: Call MCP tool
# --------------------------------------------------

async def call_mcp_tool(tool_name: str, arguments: dict):
    """
    Connect to our authenticated MCP server,
    discover the requested tool, and invoke it.
    """

    token = get_mcp_access_token()

    client = Client(
        os.environ["MCP_SERVER_URL"],
        auth=token
    )

    adapter = MCPAdapter(client)

    # Discover available MCP tools
    tools = await adapter.list_tools()

    # Find the requested tool
    selected_tool = next(
        (tool for tool in tools if tool.name == tool_name),
        None
    )

    if selected_tool is None:
        raise ValueError(
            f"MCP tool '{tool_name}' was not found."
        )

    # Invoke MCP tool
    result = await selected_tool.ainvoke(arguments)

    if not result:
        raise ValueError(
            f"MCP tool '{tool_name}' returned an empty response."
        )

    # Preserve text returned by the MCP tool
    return result[0]["text"]


# --------------------------------------------------
# 2. Fetch UK weather forecast
# --------------------------------------------------

async def fetch_uk_weather(state: dict) -> dict:
    """
    Fetch UK weather forecast using our MCP server.
    """

    # Temporary Exeter test coordinates
    latitude = 50.7184
    longitude = -3.5339

    response_text = await call_mcp_tool(
        "get_uk_forecast",
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    forecast_data = json.loads(response_text)

    return {
        "forecast": {
            "source": "Met Office",
            "data": forecast_data
        }
    }


# --------------------------------------------------
# 3. Fetch official UK weather warnings
# --------------------------------------------------

async def fetch_uk_warnings(state: dict) -> dict:
    """
    Retrieve official Met Office weather warnings
    for the selected location.
    """

    # Temporary Exeter test coordinates
    latitude = 50.7184
    longitude = -3.5339

    response_text = await call_mcp_tool(
        "get_uk_weather_warnings",
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    warnings_data = json.loads(response_text)

    return {
        "warnings": warnings_data
    }


# --------------------------------------------------
# 4. Fetch US weather forecast
# --------------------------------------------------

async def fetch_us_weather(state: dict) -> dict:
    """
    Fetch US weather forecast using our MCP server.
    """

    # Temporary New York test coordinates
    latitude = 40.7128
    longitude = -74.0060

    response_text = await call_mcp_tool(
        "get_forecast",
        {
            "latitude": latitude,
            "longitude": longitude
        }
    )

    return {
        "forecast": {
            "source": "NWS",
            "text": response_text
        }
    }


# --------------------------------------------------
# 5. Route based on country
# --------------------------------------------------

def route_by_country(state: dict) -> str:
    """
    Select the appropriate country workflow.
    """

    country = state.get("country", "").upper()

    if country == "UK":
        return "uk"

    elif country == "US":
        return "us"

    return "unsupported"


# --------------------------------------------------
# 6. Analyze weather risk
# --------------------------------------------------

def analyze_weather_risk(state: dict) -> dict:
    """
    Determine weather risk.

    UK:
        Use official Met Office warning levels.

    US:
        Use temporary keyword-based risk logic.
    """

    forecast = state["forecast"]
    source = forecast["source"]

    risk = "unknown"

    # ----------------------------------------------
    # US risk assessment
    # ----------------------------------------------

    if source == "NWS":

        weather_text = forecast["text"].lower()

        if "thunderstorm" in weather_text:
            risk = "high"

        elif "rain likely" in weather_text:
            risk = "moderate"

        else:
            risk = "low"

    # ----------------------------------------------
    # UK risk assessment
    # ----------------------------------------------

    elif source == "Met Office":

        warnings_data = state.get("warnings", {})

        # Do not report low risk if warnings were not checked
        if not warnings_data.get("warnings_checked"):
            return {
                "risk_level": "unknown"
            }

        warnings = warnings_data.get("warnings", [])

        warning_levels = {
            "RED": 3,
            "AMBER": 2,
            "YELLOW": 1
        }

        highest_level = max(
            (
                warning_levels.get(
                    warning.get("warning_level", "").upper(),
                    0
                )
                for warning in warnings
            ),
            default=0
        )

        if highest_level == 3:
            risk = "red_warning"

        elif highest_level == 2:
            risk = "amber_warning"

        elif highest_level == 1:
            risk = "yellow_warning"

        else:
            risk = "no_official_warning"

    return {
        "risk_level": risk
    }


# --------------------------------------------------
# 7. Generate final weather answer
# --------------------------------------------------

def generate_weather_answer(state: dict) -> dict:
    """
    Generate a final response for every risk level.
    """

    forecast = state.get("forecast", {})
    risk = state.get("risk_level", "unknown")
    source = forecast.get("source", "Unknown")

    # ----------------------------------------------
    # UK response
    # ----------------------------------------------

    if source == "Met Office":

        risk_messages = {
            "red_warning": (
                "A RED Met Office weather warning is active "
                "for this location."
            ),
            "amber_warning": (
                "An AMBER Met Office weather warning is active "
                "for this location."
            ),
            "yellow_warning": (
                "A YELLOW Met Office weather warning is active "
                "for this location."
            ),
            "no_official_warning": (
                "No official Met Office weather warnings "
                "were returned for this location."
            ),
            "unknown": (
                "The official weather warning status "
                "could not be verified."
            )
        }

        answer = risk_messages.get(
            risk,
            "Weather warning status is unavailable."
        )

    # ----------------------------------------------
    # US response
    # ----------------------------------------------

    elif source == "NWS":

        risk_messages = {
            "high": (
                "The forecast mentions thunderstorms. "
                "Further weather checks are recommended."
            ),
            "moderate": (
                "The forecast indicates rain is likely."
            ),
            "low": (
                "The basic keyword assessment did not "
                "detect thunderstorms or likely rain."
            ),
            "unknown": (
                "Weather risk could not be determined."
            )
        }

        answer = risk_messages.get(
            risk,
            "Weather risk information is unavailable."
        )

        answer += (
            " This is a preliminary keyword-based "
            "assessment, not an official NWS alert."
        )

    else:
        answer = "Weather information is unavailable."

    return {
        "final_answer": answer
    }


# --------------------------------------------------
# 8. Handle unsupported countries
# --------------------------------------------------

def unsupported_country(state: dict) -> dict:
    """
    Return a message for unsupported countries.
    """

    country = state.get("country", "Unknown")

    return {
        "final_answer": (
            f"Weather information for '{country}' "
            "is not currently supported. "
            "Please select the UK or US."
        )
    }
