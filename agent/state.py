
from typing import TypedDict, NotRequired


class WeatherState(TypedDict):
    # Original question entered by the user.
    user_query: str

    # Country selected in Streamlit: UK or US.
    country: str

    # City selected by the user.
    city: str

    # Coordinates supplied by Streamlit or resolved by geocoding.
    latitude: NotRequired[float]
    longitude: NotRequired[float]

    # Timezone of the selected location.
    timezone: NotRequired[str]

    # Location resolution status:
    # "resolved" or "needs_clarification".
    location_status: NotRequired[str]

    # Candidate locations returned by the geocoding API.
    # Used by Streamlit to display location choices.
    location_choices: NotRequired[list[dict]]

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
