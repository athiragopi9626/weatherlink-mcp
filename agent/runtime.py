from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent.graph import graph

app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload):
    initial_state = {
        "user_query": payload.get("user_query", ""),
        "country": payload.get("country", "UK"),
        "attempts": 0,
    }

    result = await graph.ainvoke(initial_state)

    return {
        "forecast": result.get("forecast"),
        "risk_level": result.get("risk_level"),
        "final_answer": result.get("final_answer"),
    }


if __name__ == "__main__":
    app.run()