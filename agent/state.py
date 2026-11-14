
from typing import TypedDict

class WeatherState(TypedDict):
    user_query: str
    country: str
    forecast: dict
    warnings: str
    risk_level: str
    attempts: int
    final_answer: str
