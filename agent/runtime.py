
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent.graph import graph

# Initialize the AgentCore application.
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload):
    """
    Receive requests from Streamlit or other clients
    and execute the LangGraph weather workflow.
    """

    # Build LangGraph state from the incoming request.
    initial_state = {
        "user_query": payload.get("user_query", ""),
        "country": payload.get("country", "UK"),
        "city": (payload.get("city") or "").strip(),

        # Pass dynamically resolved coordinates into LangGraph.
        # These are optional for clients that provide only a city.
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone"),

        "attempts": 0,
    }

    # Execute the LangGraph workflow.
    result = await graph.ainvoke(initial_state)

    # Return either a weather answer or a clarification request.
    return {
        "city": result.get("city"),
        "country": result.get("country"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),

        # Location resolution status and possible matches.
        "location_status": result.get(
            "location_status", "resolved"
        ),
        "location_choices": result.get("location_choices", []),

        # Weather results.
        "forecast": result.get("forecast"),
        "warnings": result.get("warnings"),
        "risk_level": result.get("risk_level"),
        "final_answer": result.get("final_answer"),
    }


if __name__ == "__main__":
    app.run()
