
"""
Met Office National Severe Weather Warnings Service (NSWWS).

This module:
1. Retrieves the API key from environment variables or AWS Secrets Manager.
2. Calls the official Met Office Atom Feed API.
3. Finds the URL for the latest issued warnings.
4. Retrieves the warnings as GeoJSON.
5. Checks whether the requested coordinates fall inside a warning area.
6. Filters warnings by date and returns a structured result.

Official API:
https://data.hub.api.metoffice.gov.uk/nswws/v1.1
"""

import asyncio
import json
import os
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import boto3
import httpx2
from dotenv import load_dotenv
from shapely.geometry import Point, shape


# Load environment variables from .env for local development.
load_dotenv()


# Official NSWWS Atom Feed endpoint.
FEED_URL = (
    "https://data.hub.api.metoffice.gov.uk"
    "/nswws/v1.1/objects/feed"
)

# Atom XML uses a namespace, so we must include it when searching XML.
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Use UK local time when a user requests a specific date.
UK_TIMEZONE = ZoneInfo("Europe/London")


def get_warning_api_key() -> str:
    """
    Get the Met Office warnings API key.

    Local development:
        Read METOFFICE_WARNING_API_KEY from .env.

    AWS AgentCore:
        Read the JSON secret from AWS Secrets Manager.
    """

    # Step 1: Check whether the key is available locally.
    api_key = os.getenv("METOFFICE_WARNING_API_KEY")

    if api_key:
        return api_key

    # Step 2: If not local, read the secret identifier.
    secret_arn = os.getenv("METOFFICE_WARNING_SECRET_ARN")

    if not secret_arn:
        raise RuntimeError(
            "METOFFICE_WARNING_API_KEY or "
            "METOFFICE_WARNING_SECRET_ARN must be configured"
        )

    # Step 3: Create an AWS Secrets Manager client.
    secrets_client = boto3.client("secretsmanager")

    # Step 4: Retrieve the secret value.
    response = secrets_client.get_secret_value(
        SecretId=secret_arn
    )

    # Our secret was stored as JSON.
    secret_data = json.loads(response["SecretString"])

    # Extract the specific key from the JSON.
    api_key = secret_data.get("METOFFICE_WARNING_API_KEY")

    if not api_key:
        raise RuntimeError(
            "METOFFICE_WARNING_API_KEY not found in AWS secret"
        )

    return api_key


def parse_timestamp(timestamp: str) -> datetime:
    """
    Convert an API timestamp into a Python datetime.

    Example:
        2026-07-08T10:51:23Z

    The Z indicates UTC.
    """

    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def get_date_window(date: str):
    """
    Convert a requested UK date into a UTC time range.

    Example:
        date = "2026-11-16"

    This lets us check whether a warning overlaps that day,
    including when the UK is observing daylight saving time.
    """

    requested_date = datetime.strptime(
        date, "%Y-%m-%d"
    ).date()

    # Start of the requested day in UK local time.
    start_local = datetime.combine(
        requested_date,
        datetime.min.time(),
        tzinfo=UK_TIMEZONE,
    )

    # Start of the following day.
    end_local = datetime.combine(
        requested_date + timedelta(days=1),
        datetime.min.time(),
        tzinfo=UK_TIMEZONE,
    )

    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


def extract_issued_url(xml_content: bytes) -> str:
    """
    Extract the current issued-warnings URL from the Atom Feed.

    The Met Office documentation says:
    - Look for the feed-level link with rel="related".
    - Read its href attribute.
    - Do not manually construct the URL using a UUID.
    """

    # Convert the XML response into an XML element tree.
    root = ET.fromstring(xml_content)

    # Search only the feed-level link elements.
    for link in root.findall("atom:link", ATOM_NS):

        if link.get("rel") != "related":
            continue

        # The href contains the current issued-warnings URL.
        issued_url = link.get("href", "")

        # Validate the URL before making another HTTP request.
        parsed_url = urlparse(issued_url)

        if (
            parsed_url.scheme == "https"
            and parsed_url.hostname
            == "data.hub.api.metoffice.gov.uk"
            and parsed_url.path.startswith(
                "/nswws/v1.1/objects/issued/"
            )
        ):
            return issued_url

    raise ValueError(
        "Issued-warnings URL not found in Atom Feed"
    )


async def get_uk_weather_warnings(
    latitude: float,
    longitude: float,
    date: str | None = None,
) -> dict:
    """
    Retrieve official Met Office warnings for a location.

    Parameters:
        latitude: Latitude of the requested location.
        longitude: Longitude of the requested location.
        date: Optional UK date in YYYY-MM-DD format.

    Returns:
        Dictionary containing matching official warnings.
    """

    # Step 1: Validate the supplied coordinates.
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180")

    # Step 2: Decide which time period to check.
    if date:
        window_start, window_end = get_date_window(date)
    else:
        # Without a date, find warnings still relevant now.
        window_start = datetime.now(timezone.utc)
        window_end = None

    # Step 3: Read the API key without blocking the event loop.
    api_key = await asyncio.to_thread(get_warning_api_key)

    # Met Office uses the apikey header for authentication.
    headers = {
        "apikey": api_key,
    }

    # Step 4: Call the two NSWWS endpoints.
    async with httpx2.AsyncClient(timeout=30.0) as client:

        # First request: retrieve the Atom Feed.
        feed_response = await client.get(
            FEED_URL,
            headers={
                **headers,
                "Accept": "application/atom+xml",
            },
        )

        # Raise an error for unsuccessful HTTP responses.
        feed_response.raise_for_status()

        # Read the issued-warnings URL from the Atom XML.
        issued_url = extract_issued_url(
            feed_response.content
        )

        # Second request: retrieve the latest warnings as GeoJSON.
        warnings_response = await client.get(
            issued_url,
            headers={
                **headers,
                "Accept": "application/geo+json",
            },
        )

        warnings_response.raise_for_status()

        # Convert the GeoJSON response into a Python dictionary.
        warnings_data = warnings_response.json()

    # Step 5: Validate the expected GeoJSON structure.
    if warnings_data.get("type") != "FeatureCollection":
        raise ValueError(
            "Unexpected response from Met Office warnings API"
        )

    features = warnings_data.get("features")

    if not isinstance(features, list):
        raise ValueError("Missing GeoJSON features list")

    # Shapely expects longitude first, then latitude.
    user_location = Point(longitude, latitude)

    matching_warnings = []

    # Step 6: Examine each official warning.
    for feature in features:

        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")

        if not geometry:
            continue

        # The issued collection should contain issued warnings.
        if properties.get("warningStatus") != "ISSUED":
            continue

        # Convert GeoJSON MultiPolygon into a Shapely geometry.
        warning_area = shape(geometry)

        # Skip warnings that do not cover the user's location.
        # covers() includes points exactly on a polygon boundary.
        if not warning_area.covers(user_location):
            continue

        # Read the warning's validity period.
        valid_from = parse_timestamp(
            properties["validFromDate"]
        )

        valid_to = parse_timestamp(
            properties["validToDate"]
        )

        # Step 7: Check whether the warning overlaps the date.
        if window_end is None:
            overlaps = valid_to >= window_start
        else:
            overlaps = (
                valid_from < window_end
                and valid_to >= window_start
            )

        if not overlaps:
            continue

        # Step 8: Return useful official warning information.
        matching_warnings.append({
            "warning_id": properties.get("warningId"),
            "warning_level": properties.get("warningLevel"),
            "warning_status": properties.get("warningStatus"),
            "weather_types": properties.get("weatherType", []),
            "headline": properties.get("warningHeadline"),
            "valid_from": properties.get("validFromDate"),
            "valid_to": properties.get("validToDate"),
            "issued_at": properties.get("issuedDate"),
            "affected_areas": properties.get("affectedAreas", []),
            "what_to_expect": properties.get("whatToExpect", []),
            "what_should_i_do": properties.get("whatShouldIDo"),
            "further_details": properties.get(
                "warningFurtherDetails"
            ),
        })

    # Step 9: Return a structured response to the MCP tool.
    return {
        "source": "Met Office NSWWS",
        "latitude": latitude,
        "longitude": longitude,
        "requested_date": date,
        "warnings_checked": True,
        "warning_count": len(matching_warnings),
        "warnings": matching_warnings,
    }


# This block runs only when executing this file directly.
# It does not run when the MCP server imports this module.
async def main():

    # Exeter coordinates are used ONLY for local testing.
    # Later, geocoding will supply coordinates dynamically.
    result = await get_uk_weather_warnings(
        latitude=50.7184,
        longitude=-3.5339,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
