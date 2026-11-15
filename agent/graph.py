
import asyncio

from langgraph.graph import StateGraph, START, END

from agent.state import WeatherState

from agent.nodes import (
    resolve_location,
    fetch_uk_weather,
    fetch_uk_warnings,
    fetch_us_weather,
    route_by_country,
    analyze_weather_risk,
    generate_weather_answer,
    unsupported_country,
)


# --------------------------------------------------
# 1. Route after location resolution
# --------------------------------------------------

def route_after_location(state: WeatherState) -> str:
    """
    Decide whether to continue fetching weather
    or ask the user to clarify their location.
    """

    # Multiple locations matched the user's city.
    # Stop the graph and return choices to the UI.
    if state.get("location_status") == "needs_clarification":
        return "clarification"

    # Location resolved successfully.
    # Continue with the appropriate weather provider.
    return route_by_country(state)


# --------------------------------------------------
# 2. Create LangGraph workflow
# --------------------------------------------------

builder = StateGraph(WeatherState)


# --------------------------------------------------
# 3. Register nodes
# --------------------------------------------------

# Resolve city into geographic coordinates.
builder.add_node("resolve_location", resolve_location)

# UK weather forecast from Met Office MCP tool.
builder.add_node("fetch_uk", fetch_uk_weather)

# Official UK weather warnings.
builder.add_node("fetch_uk_warnings", fetch_uk_warnings)

# US weather forecast from NWS MCP tool.
builder.add_node("fetch_us", fetch_us_weather)

# Analyze weather risks.
builder.add_node("analyze_risk", analyze_weather_risk)

# Generate natural-language answer using Amazon Bedrock.
builder.add_node("generate_answer", generate_weather_answer)

# Handle unsupported countries.
builder.add_node("unsupported", unsupported_country)


# --------------------------------------------------
# 4. Start workflow - select country
# --------------------------------------------------

builder.add_conditional_edges(
    START,
    route_by_country,
    {
        "uk": "resolve_location",
        "us": "resolve_location",
        "unsupported": "unsupported",
    }
)


# --------------------------------------------------
# 5. Resolve location and handle ambiguity
# --------------------------------------------------

builder.add_conditional_edges(
    "resolve_location",
    route_after_location,
    {
        # Multiple locations found.
        # Return clarification response without an exception.
        "clarification": END,

        # UK location resolved.
        "uk": "fetch_uk",

        # US location resolved.
        "us": "fetch_us",

        # Unsupported country.
        "unsupported": "unsupported",
    }
)


# --------------------------------------------------
# 6. UK weather workflow
# --------------------------------------------------

# Fetch UK weather forecast.
builder.add_edge("fetch_uk", "fetch_uk_warnings")

# Retrieve warnings and analyze risk.
builder.add_edge("fetch_uk_warnings", "analyze_risk")


# --------------------------------------------------
# 7. US weather workflow
# --------------------------------------------------

# US forecast goes directly to risk analysis.
builder.add_edge("fetch_us", "analyze_risk")


# --------------------------------------------------
# 8. Generate weather answer
# --------------------------------------------------

# After analyzing risk, invoke Bedrock LLM.
builder.add_edge("analyze_risk", "generate_answer")

# End after generating the response.
builder.add_edge("generate_answer", END)


# --------------------------------------------------
# 9. Unsupported country
# --------------------------------------------------

builder.add_edge("unsupported", END)


# --------------------------------------------------
# 10. Compile LangGraph
# --------------------------------------------------

graph = builder.compile()


# --------------------------------------------------
# 11. Local test
# --------------------------------------------------

async def main():

    # Test city-only input.
    # If multiple locations match, the graph should
    # return choices without calling MCP or Bedrock.
    # initial_state = {
    #     "user_query": "What's the weather in Manchester?",
    #     "country": "UK",
    #     "city": "Manchester",
    #     "attempts": 0,
    # }

    initial_state = {
    "user_query": "Will it rain in Manchester tomorrow? Should I carry an umbrella?",
    "country": "UK",
    "city": "Manchester",
    "latitude": 53.48095,
    "longitude": -2.23743,
    "timezone": "Europe/London",
    "attempts": 0,
}

    result = await graph.ainvoke(initial_state)

    print("\n========== WEATHER RESULT ==========")

    print("\nCity:")
    print(result.get("city"))

    print("\nCountry:")
    print(result.get("country"))

    print("\nLocation status:")
    print(result.get("location_status", "unknown"))

    print("\nLocation choices:")
    print(result.get("location_choices", []))

    print("\nForecast:")
    print(result.get("forecast", "Not available"))

    print("\nOfficial warnings:")
    print(result.get("warnings", "Not available"))

    print("\nRisk level:")
    print(result.get("risk_level", "unknown"))

    print("\nFinal answer:")
    print(result.get("final_answer"))

    print("\n====================================")


# --------------------------------------------------
# 12. Run local test
# --------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
