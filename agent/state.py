from typing import TypedDict, NotRequired


class WeatherState(TypedDict):
    # Original question entered by the user.
    user_query: str

    # Country selected in Streamlit: UK or US.
    country: str

    # City selected in Streamlit, e.g. Exeter or Manchester.
    city: str

    # Coordinates populated by our geocoding node.
    latitude: NotRequired[float]
    longitude: NotRequired[float]

    # Timezone returned by the geocoding service.
    timezone: NotRequired[str]

    # Weather data returned by MCP tools.
    forecast: NotRequired[dict]

    # Official weather warnings.
    warnings: NotRequired[dict]

    # Risk level calculated by LangGraph.
    risk_level: NotRequired[str]

    # Reserved for retry handling.
    attempts: int

    # Final response shown in Streamlit.
    final_answer: NotRequired[str]