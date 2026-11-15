
import httpx


def search_locations(city: str, country: str) -> list[dict]:
    """
    Search for locations using the Open-Meteo Geocoding API.

    Args:
        city: City name entered by the user, e.g. "Manchester".
        country: Country selected in Streamlit, e.g. "UK" or "US".

    Returns:
        A list of matching locations containing:
        - name
        - admin1 (state/region)
        - country
        - latitude
        - longitude
        - timezone
    """

    # Convert our application country codes to ISO country codes.
    country_codes = {
        "UK": "GB",
        "US": "US",
    }

    country_code = country_codes.get(country)

    # Do not search if the city is empty or country unsupported.
    if not city.strip() or not country_code:
        return []

    # Open-Meteo Geocoding API endpoint.
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # Search parameters.
    params = {
        "name": city.strip(),
        "count": 10,
        "language": "en",
        "format": "json",
        "countryCode": country_code,
    }

    try:
        # Send the HTTP GET request to Open-Meteo.
        response = httpx.get(
            url,
            params=params,
            timeout=10.0,
        )

        # Raise an exception for unsuccessful HTTP responses.
        response.raise_for_status()

        # Convert the JSON response into a Python dictionary.
        data = response.json()

        # Return matching locations, or an empty list if none found.
        return data.get("results", [])

    except (httpx.HTTPError, ValueError) as exc:
        # Surface the failure so Streamlit can display an error.
        raise RuntimeError(
            f"Location search failed: {exc}"
        ) from exc
