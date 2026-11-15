
import json
import os
import uuid

import boto3
import streamlit as st

# Import our location search helper.
# This file should exist at ui/location_search.py.
from location_search import search_locations

from pathlib import Path
from dotenv import load_dotenv

# Locate the project root and load its .env file.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
# --------------------------------------------------
# 1. AWS AgentCore configuration
# --------------------------------------------------

# AWS Region where our LangGraph agent is deployed.
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# ARN of the deployed LangGraph AgentCore runtime.
AGENT_ARN = os.environ["AGENT_RUNTIME_ARN"]

# Create the AWS client used to invoke AgentCore.
client = boto3.client(
    "bedrock-agentcore",
    region_name=AWS_REGION,
)


# --------------------------------------------------
# 2. Configure Streamlit page
# --------------------------------------------------

st.set_page_config(
    page_title="WeatherLink AI",
    page_icon="🌤️",
    layout="wide",
)

st.title("🌤️ WeatherLink AI")

st.caption(
    "Weather intelligence powered by LangGraph, "
    "MCP and Amazon Bedrock AgentCore"
)


# --------------------------------------------------
# 3. Initialize Streamlit session state
# --------------------------------------------------

# Store chat messages between Streamlit reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Keep a unique session ID for AgentCore requests.
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Store the location confirmed by the user.
if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

# Store geocoding search results.
if "location_results" not in st.session_state:
    st.session_state.location_results = []

# Track the search query associated with the results.
if "location_search_key" not in st.session_state:
    st.session_state.location_search_key = None


# --------------------------------------------------
# 4. Sidebar: location search and settings
# --------------------------------------------------

with st.sidebar:

    st.header("📍 Location Settings")

    # Select the country/weather provider.
    country_name = st.selectbox(
        "Country",
        ["United Kingdom", "United States"],
        key="country_selector",
    )

    # Convert display name to LangGraph country code.
    country = (
        "UK"
        if country_name == "United Kingdom"
        else "US"
    )

    # Suggested search text for each country.
    default_city = (
        "Exeter"
        if country == "UK"
        else "New York"
    )

    # Let the user type a city name.
    city_search = st.text_input(
        "Search city",
        value=default_city,
        key=f"city_search_{country}",
        help="Enter a city name or partial city name.",
    )

    # Identify the exact country and search text.
    # This helps detect changes after a Streamlit rerun.
    current_search_key = (
        country,
        city_search.strip().casefold(),
    )

    # Invalidate old results if the user changes
    # either the country or the city search text.
    if (
        st.session_state.location_search_key
        != current_search_key
    ):
        st.session_state.location_results = []
        st.session_state.selected_location = None
        st.session_state.location_search_key = (
            current_search_key
        )

    # Search the geocoding service only when clicked.
    if st.button(
        "🔍 Search Location",
        use_container_width=True,
    ):

        # Clear any previously selected location.
        st.session_state.selected_location = None

        try:
            with st.spinner("Searching locations..."):

                # Fetch candidate locations.
                locations = search_locations(
                    city_search,
                    country,
                )

                # Save results for subsequent reruns.
                st.session_state.location_results = (
                    locations
                )

            if not locations:
                st.warning(
                    "No locations found. "
                    "Try another spelling or a nearby city."
                )

        except Exception as exc:
            st.session_state.location_results = []
            st.error("Unable to search locations.")
            st.exception(exc)

    # Read the saved search results.
    locations = st.session_state.location_results

    if locations:

        # Format each location so users can distinguish
        # places that share the same city name.
        def format_location(index):
            place = locations[index]

            parts = [
                place.get("name"),
                place.get("admin1"),
                place.get("country"),
            ]

            return ", ".join(
                str(part)
                for part in parts
                if part
            )

        # User must explicitly select a search result.
        selected_index = st.selectbox(
            "Select the correct location",
            options=range(len(locations)),
            format_func=format_location,
            index=None,
            placeholder="Choose a location...",
            key=f"location_choice_{current_search_key}",
        )

        if selected_index is not None:

            selected_place = locations[selected_index]

            # Store the confirmed coordinates.
            st.session_state.selected_location = {
                "city": selected_place["name"],
                "country": country,
                "latitude": selected_place["latitude"],
                "longitude": selected_place["longitude"],
                "timezone": selected_place.get(
                    "timezone", "UTC"
                ),
                "display_name": format_location(
                    selected_index
                ),
            }

            st.success(
                "Location selected successfully."
            )

    # Show the current confirmed location.
    location = st.session_state.selected_location

    if location:
        st.caption(
            f"Selected: {location['display_name']}"
        )
    else:
        st.caption(
            "Search and select a location to continue."
        )

    st.divider()

    # Display information about the application.
    st.subheader("⚙️ Technology")

    st.write("**Agent framework:** LangGraph")
    st.write("**Runtime:** AWS AgentCore")
    st.write("**Tool integration:** MCP")
    st.write("**Weather providers:** Met Office / NWS")

    st.divider()

    # Clear chat history and start a fresh session.
    if st.button(
        "🗑️ New Conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.session_id = str(
            uuid.uuid4()
        )

        st.rerun()


# --------------------------------------------------
# 5. Main page: selected location
# --------------------------------------------------

location = st.session_state.selected_location

if location:

    st.info(
        f"📍 Current location: "
        f"{location['display_name']}"
    )

else:

    st.info(
        "👈 Search and select a location "
        "from the sidebar to get started."
    )


# --------------------------------------------------
# 6. Display previous chat messages
# --------------------------------------------------

# Each assistant message can contain a structured
# result so its details survive Streamlit reruns.
for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])

        if message["role"] == "assistant":

            result = message.get("result")

            if result:

                # Display the risk assessment.
                risk = result.get(
                    "risk_level", "unknown"
                )

                st.markdown("**🛡️ Weather Risk**")

                st.write(
                    risk.replace("_", " ").title()
                )

                # Display official warning information.
                warnings = result.get("warnings") or {}

                st.markdown("**⚠️ Official Warnings**")

                if warnings.get("warnings_checked"):

                    warning_items = warnings.get(
                        "warnings", []
                    )

                    if not warning_items:
                        st.success(
                            "No official warnings returned."
                        )
                    else:
                        st.warning(
                            f"{len(warning_items)} "
                            "official warning(s) returned."
                        )

                        for warning in warning_items:
                            st.json(warning)

                else:
                    st.info(
                        "Official warning information "
                        "is unavailable for this response."
                    )

                # Keep the large forecast JSON collapsed.
                with st.expander(
                    "📊 Detailed Weather Forecast"
                ):
                    st.json(
                        result.get("forecast") or {}
                    )


# --------------------------------------------------
# 7. Accept a weather question
# --------------------------------------------------

prompt = st.chat_input(
    "Ask about the weather...",
    disabled=(location is None),
)

if prompt:

    # Copy the confirmed location for this request.
    # This prevents the response from being associated
    # with a later location selection.
    request_location = dict(
        st.session_state.selected_location
    )

    # Save the user message.
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
    })

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):

        with st.spinner("Analyzing weather conditions..."):

            try:

                # ----------------------------------
                # 8. Prepare the AgentCore payload
                # ----------------------------------

                # Send the question and the location
                # selected by the user.
                payload = {
                    "user_query": prompt,
                    "country": request_location["country"],
                    "city": request_location["city"],
                    "latitude": request_location["latitude"],
                    "longitude": request_location["longitude"],
                    "timezone": request_location["timezone"],
                    "attempts": 0,
                }

                # ----------------------------------
                # 9. Invoke the deployed agent
                # ----------------------------------

                response = client.invoke_agent_runtime(
                    agentRuntimeArn=AGENT_ARN,
                    runtimeSessionId=(
                        st.session_state.session_id
                    ),
                    contentType="application/json",
                    accept="application/json",
                    payload=json.dumps(
                        payload
                    ).encode("utf-8"),
                )

                # Read and decode the response body.
                raw_response = (
                    response["response"].read()
                )

                result = json.loads(
                    raw_response
                )

                # ----------------------------------
                # 10. Extract final answer
                # ----------------------------------

                answer = result.get(
                    "final_answer"
                ) or (
                    "The agent did not return "
                    "a weather summary."
                )

                # Display the generated answer.
                st.markdown("### 🌤️ Weather Summary")

                st.write(answer)

                # ----------------------------------
                # 11. Display weather risk
                # ----------------------------------

                risk = result.get(
                    "risk_level", "unknown"
                )

                st.markdown("### 🛡️ Weather Risk")

                st.write(
                    risk.replace("_", " ").title()
                )

                # ----------------------------------
                # 12. Display official warnings
                # ----------------------------------

                warnings = result.get("warnings") or {}

                st.markdown("### ⚠️ Official Warnings")

                if warnings.get("warnings_checked"):

                    warning_items = warnings.get(
                        "warnings", []
                    )

                    if not warning_items:

                        st.success(
                            "No official warnings returned "
                            "for the selected location."
                        )

                    else:

                        st.warning(
                            f"{len(warning_items)} "
                            "official warning(s) returned."
                        )

                        for warning in warning_items:
                            st.json(warning)

                else:

                    st.info(
                        "Official warning information "
                        "is not available."
                    )

                # ----------------------------------
                # 13. Detailed forecast
                # ----------------------------------

                with st.expander(
                    "📊 Detailed Weather Forecast"
                ):
                    st.json(
                        result.get("forecast") or {}
                    )

                # ----------------------------------
                # 14. Save successful response
                # ----------------------------------

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "result": result,
                })

            except Exception as exc:

                # Display a friendly error message.
                answer = (
                    "Unable to retrieve the weather "
                    "forecast. Please try again."
                )

                st.error(answer)

                # Show technical details during development.
                st.exception(exc)

                # Save the failed response to history.
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })
