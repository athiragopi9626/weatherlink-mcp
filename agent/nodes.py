
import json
from langchain.mcp import MCPAdapter
import os
from agent.mcp_auth import get_mcp_access_token
from fastmcp import Client


async def fetch_uk_weather(state: dict) -> dict:
    """LangGraph node that fetches UK weather using MCP."""

    # Connect to our running MCP weather server.

    token = get_mcp_access_token()

    client = Client(
        os.environ["MCP_SERVER_URL"],
        auth=token
    )

    adapter = MCPAdapter(client)

    # Discover available MCP tools.
    tools = await adapter.list_tools()

    # Select the UK weather forecast tool.
    uk_tool = next(
        tool for tool in tools
        if tool.name == "get_uk_forecast"
    )

    # Call the MCP tool using location coordinates.
    result = await uk_tool.ainvoke({
        "latitude": 50.7184,
        "longitude": -3.5339
    })

    # Extract and parse the JSON from the MCP text content.
    forecast = json.loads(result[0]["text"])

    # Return the updated LangGraph state.
    return {
    "forecast": {
        "source": "Met Office",
        "data": forecast
    }
}

def route_by_country(state: dict) -> str:
    """Choose which weather node should execute."""

    # Read the country from LangGraph state.
    country = state["country"]

    if country == "UK":
        return "uk"

    elif country == "US":
        return "us"

    else:
        return "unsupported"



async def fetch_us_weather(state: dict) -> dict:
    """Fetch US weather using our MCP server."""

    token = get_mcp_access_token()

    client = Client(
        os.environ["MCP_SERVER_URL"],
        auth=token
    )

    adapter = MCPAdapter(client)

    # Discover available tools.
    tools = await adapter.list_tools()

    # Find the US forecast tool.
    us_tool = next(
        tool for tool in tools
        if tool.name == "get_forecast"
    )

    # Use test coordinates for New York City.
    result = await us_tool.ainvoke({
        "latitude": 40.7128,
        "longitude": -74.0060
    })

    # Return the MCP response in LangGraph state.
    return {
    "forecast": {
        "source": "NWS",
        "text": result[0]["text"]
    }
}


def analyze_weather_risk(state: dict) -> dict:
    """Analyze weather conditions and update risk_level."""

    # Read the forecast saved by the previous node.
    forecast = state["forecast"]

    # Start with an unknown risk level.
    risk = "unknown"

    if forecast["source"] == "NWS":
        # Extract the US weather forecast text.
        weather_text = forecast["text"].lower()

        # Simple demonstration rules.
        if "thunderstorm" in weather_text:
            risk = "high"
        elif "rain likely" in weather_text:
            risk = "moderate"
        else:
            risk = "low"

    elif forecast["source"] == "Met Office":
        # Extract the structured UK hourly forecast.
        hours = forecast["data"]["forecast"]

        # Check the highest rain probability.
        max_rain_probability = max(
            (hour["rain_probability_percent"] for hour in hours),
            default=0
        )

        if max_rain_probability >= 80:
            risk = "high"
        elif max_rain_probability >= 50:
            risk = "moderate"
        else:
            risk = "low"

    # Update only the risk_level field in LangGraph state.
    return {"risk_level": risk}
    #     # TEMPORARY: Force high risk to test the routing.
    # risk = "high"

    # # Update the LangGraph state.
    # return {"risk_level": risk}



def review_high_risk(state: dict) -> dict:
    """Record that high-risk weather needs further review."""

    # Read the existing risk level.
    risk = state["risk_level"]

    # Prepare a message for the next stage.
    message = (
        f"Weather risk is {risk}. "
        "Additional weather checks are recommended."
    )

    # Update the shared state.
    return {"final_answer": message}

def route_by_risk(state: dict) -> str:
    """Decide whether to review the weather or finish."""

    # Read the risk calculated by analyze_weather_risk().
    risk = state["risk_level"]

    # High risk requires additional review.
    if risk == "high":
        return "review"

    # For other risk levels, finish the workflow.
    return "finish"
