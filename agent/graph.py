
import asyncio

# StateGraph creates the workflow.
# START and END mark where execution begins and finishes.
from langgraph.graph import StateGraph, START, END

# Import our shared state structure.
from agent.state import WeatherState

from agent.nodes import (
    fetch_uk_weather,
    fetch_us_weather,
    route_by_country,
    analyze_weather_risk,
    route_by_risk,
    review_high_risk,
)

builder = StateGraph(WeatherState)

# Register the two Python functions as nodes.
builder.add_node("fetch_uk", fetch_uk_weather)
builder.add_node("fetch_us", fetch_us_weather)
builder.add_node("analyze_risk", analyze_weather_risk)
builder.add_node("review_high_risk", review_high_risk)

# Choose the node based on the country.
builder.add_conditional_edges(
    START,
    route_by_country,
    {
        "uk": "fetch_uk",
        "us": "fetch_us",
    }
)

builder.add_conditional_edges(
    "analyze_risk",
    route_by_risk,
    {
        "review": "review_high_risk",
        "finish": END,
    }
)

# 4. Both weather nodes lead to risk analysis
builder.add_edge("fetch_uk", "analyze_risk")
builder.add_edge("fetch_us", "analyze_risk")

# 5. End the workflow after risk analysis
builder.add_edge("review_high_risk", END)

graph = builder.compile()


async def main():
    # Initial values for our shared state.
    initial_state = {
        "user_query": "What's the weather in New York?",
        "country": "US",
        "attempts": 0,
    }

    # Execute the graph asynchronously because our MCP node uses await.
    result = await graph.ainvoke(initial_state)

    # Display the forecast saved in the final state.
    print("Forecast:", result["forecast"])
    print("Risk level:", result["risk_level"])
    print("Final answer:", result.get("final_answer"))


if __name__ == "__main__":
    asyncio.run(main())
