from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent.graph import graph

# Initialize the AgentCore application.
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload):
    """
    Receive requests from Streamlit and execute
    the LangGraph weather workflow.
    """

    # Build the initial state from the Streamlit request.
    initial_state = {
        "user_query": payload.get("user_query", ""),
        "country": payload.get("country", "UK"),
        "city": payload.get("city", "").strip(),
        "attempts": 0,
    }

    # Execute the LangGraph workflow.
    result = await graph.ainvoke(initial_state)

    # Return the results to the Streamlit UI.
    return {
        "city": result.get("city"),
        "country": result.get("country"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "forecast": result.get("forecast"),
        "warnings": result.get("warnings"),
        "risk_level": result.get("risk_level"),
        "final_answer": result.get("final_answer"),
    }


if __name__ == "__main__":
    # Start the AgentCore runtime server.
    app.run()