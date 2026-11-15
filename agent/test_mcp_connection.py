
import asyncio

# Import the LangChain MCP adapter.
from langchain.mcp import MCPAdapter


# Define an asynchronous function so we can use await.
async def main():

    # Connect to our local weather MCP server.
    adapter = MCPAdapter(os.environ["MCP_SERVER_URL"])

    # Wait for the MCP server to return its available tools.
    tools = await adapter.list_tools()

    # Print each discovered tool.

    # Find our UK forecast tool from the discovered MCP tools.
    uk_tool = next(
        tool for tool in tools
        if tool.name == "get_uk_forecast"
    )

    # Execute the tool through the MCP connection.
    # This sends the coordinates to our running MCP server.
    result = await uk_tool.ainvoke({
        "latitude": 50.7184,
        "longitude": -3.5339
    })

    # Print the response returned by the MCP server.
    print("UK weather forecast:")
    print(result)


if __name__ == "__main__":
    # Start the asynchronous event loop.
    asyncio.run(main())
