
import asyncio

from langgraph.graph import StateGraph, START, END

from agent.state import WeatherState

from agent.nodes import (
    fetch_uk_weather,
    fetch_uk_warnings,
    fetch_us_weather,
    route_by_country,
    analyze_weather_risk,
    generate_weather_answer,
    unsupported_country,
)


# --------------------------------------------------
# 1. Create LangGraph workflow
# --------------------------------------------------

builder = StateGraph(WeatherState)


# --------------------------------------------------
# 2. Register nodes
# --------------------------------------------------

# Weather forecast nodes
builder.add_node("fetch_uk", fetch_uk_weather)
builder.add_node("fetch_us", fetch_us_weather)

# Official UK weather warnings
builder.add_node("fetch_uk_warnings", fetch_uk_warnings)

# Risk assessment
builder.add_node("analyze_risk", analyze_weather_risk)

# Final response generation
builder.add_node("generate_answer", generate_weather_answer)

# Handle unsupported countries
builder.add_node("unsupported", unsupported_country)


# --------------------------------------------------
# 3. Route based on country
# --------------------------------------------------

builder.add_conditional_edges(
    START,
    route_by_country,
    {
        "uk": "fetch_uk",
        "us": "fetch_us",
        "unsupported": "unsupported",
    }
)


# --------------------------------------------------
# 4. UK workflow
# --------------------------------------------------

# Fetch UK forecast first
# Then retrieve official Met Office warnings
builder.add_edge("fetch_uk", "fetch_uk_warnings")

# Continue to risk assessment
builder.add_edge("fetch_uk_warnings", "analyze_risk")


# --------------------------------------------------
# 5. US workflow
# --------------------------------------------------

# US forecast goes directly to risk assessment
builder.add_edge("fetch_us", "analyze_risk")


# --------------------------------------------------
# 6. Risk assessment and response
# --------------------------------------------------

# Generate a response for every risk level
builder.add_edge("analyze_risk", "generate_answer")

# Finish after generating the answer
builder.add_edge("generate_answer", END)


# --------------------------------------------------
# 7. Unsupported country
# --------------------------------------------------

builder.add_edge("unsupported", END)


# --------------------------------------------------
# 8. Compile graph
# --------------------------------------------------

graph = builder.compile()


# --------------------------------------------------
# 9. Test workflow
# --------------------------------------------------

async def main():

    # Change country to "UK" to test Met Office.
    # Current test uses New York, US.

    initial_state = {
        "user_query": "What's the weather in New York?",
        "country": "US",
        "attempts": 0,
    }

    # Execute the workflow asynchronously
    result = await graph.ainvoke(initial_state)

    # Display results
    print("\n========== WEATHER RESULT ==========")

    print("\nCountry:")
    print(result.get("country"))

    print("\nForecast:")
    print(result.get("forecast"))

    print("\nOfficial warnings:")
    print(result.get("warnings", "Not available"))

    print("\nRisk level:")
    print(result.get("risk_level", "unknown"))

    print("\nFinal answer:")
    print(result.get("final_answer"))

    print("\n====================================")


# --------------------------------------------------
# 10. Run application
# --------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
