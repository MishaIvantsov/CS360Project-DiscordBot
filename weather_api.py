from __future__ import annotations
import asyncio
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)

# Seattle, WA
SEATTLE_LAT = 47.6062
SEATTLE_LON = -122.3321
TIMEZONE = "America/Los_Angeles"
REQUEST_TIMEOUT = 10  # seconds

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_DAILY_VARS = ",".join(
    [
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
    ]
)

# WMO weather interpretation codes -> (emoji, description)
_WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Drizzle"),
    55: ("🌦️", "Dense drizzle"),
    61: ("🌧️", "Light rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("🌨️", "Light snow"),
    73: ("🌨️", "Snow"),
    75: ("❄️", "Heavy snow"),
    77: ("🌨️", "Snow grains"),
    80: ("🌦️", "Light showers"),
    81: ("🌧️", "Showers"),
    82: ("⛈️", "Violent showers"),
    85: ("🌨️", "Snow showers"),
    86: ("❄️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm with hail"),
    99: ("⛈️", "Severe thunderstorm"),
}


def _describe(code: int) -> tuple[str, str]:
    return _WMO_CODES.get(code, ("🌡️", "Unknown conditions"))


def _fetch_forecast(iso_date: str) -> dict:
    """Blocking HTTP GET to Open-Meteo for a single day in Seattle."""
    params = urllib.parse.urlencode(
        {
            "latitude": SEATTLE_LAT,
            "longitude": SEATTLE_LON,
            "daily": _DAILY_VARS,
            "temperature_unit": "fahrenheit",
            "timezone": TIMEZONE,
            "start_date": iso_date,
            "end_date": iso_date,
        }
    )
    url = f"{FORECAST_URL}?{params}"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:  # nosec B310
        return json.loads(resp.read().decode())


async def get_weather_summary(date_str: str) -> str | None:
    """Return a one-line Seattle weather summary for a date (MM.DD.YYYY).

    Returns None if the date is invalid, outside the forecast range, or the
    request fails. Callers should treat None as "no weather to show" and never
    let it break the surrounding command.
    """
    try:
        iso_date = datetime.strptime(date_str, "%m.%d.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(_fetch_forecast, iso_date),
            timeout=REQUEST_TIMEOUT + 2,
        )
    except Exception:
        logger.warning("weather fetch failed for %s", date_str, exc_info=True)
        return None

    daily = data.get("daily") or {}
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_probability_max") or []

    if not codes or codes[0] is None:
        return None  # date is outside the available forecast range

    emoji, desc = _describe(int(codes[0]))
    parts = [f"{emoji} {desc}"]
    if highs and highs[0] is not None and lows and lows[0] is not None:
        parts.append(f"High {round(highs[0])}°F / Low {round(lows[0])}°F")
    if precip and precip[0] is not None:
        parts.append(f"{round(precip[0])}% precip")
    return " · ".join(parts)
