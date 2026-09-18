from datetime import date, timedelta

import requests
from flask import jsonify, request, send_from_directory

from app import app

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def api_get(url, params):
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def weather_description(code):
    codes = {
        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Drizzle", "🌦️"),
        55: ("Dense drizzle", "🌧️"),
        56: ("Freezing drizzle", "🌧️"),
        57: ("Dense freezing drizzle", "🌧️"),
        61: ("Light rain", "🌦️"),
        63: ("Rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Light freezing rain", "🌧️"),
        67: ("Heavy freezing rain", "🌧️"),
        71: ("Light snow", "🌨️"),
        73: ("Snow", "🌨️"),
        75: ("Heavy snow", "❄️"),
        77: ("Snow grains", "❄️"),
        80: ("Light showers", "🌦️"),
        81: ("Showers", "🌧️"),
        82: ("Heavy showers", "⛈️"),
        85: ("Snow showers", "🌨️"),
        86: ("Heavy snow showers", "❄️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with hail", "⛈️"),
        99: ("Severe thunderstorm", "⛈️"),
    }
    return codes.get(code, ("Unknown", "🌡️"))


def number(value, digits=0):
    if value is None:
        return None
    return round(value, digits)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/server/coordinates")
def get_coordinates():
    city_name = request.args.get("city_name", "").strip()
    if not city_name:
        return jsonify([])

    try:
        data = api_get(
            GEOCODING_URL,
            {"name": city_name, "count": 8, "language": "en", "format": "json"},
        )
        results = []
        for location in data.get("results", []):
            parts = [location.get("name", "Unknown")]
            if location.get("admin1") and location["admin1"] != location.get("name"):
                parts.append(location["admin1"])
            if location.get("country"):
                parts.append(location["country"])
            results.append(
                {
                    "lat": location["latitude"],
                    "lon": location["longitude"],
                    "location": ", ".join(parts),
                    "country": location.get("country", ""),
                    "timezone": location.get("timezone", "UTC"),
                }
            )
        return jsonify(results)
    except requests.RequestException:
        return jsonify({"error": "Location service is temporarily unavailable."}), 503


@app.route("/server/current_weather")
def get_current_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude are required."}), 400

    try:
        data = api_get(
            FORECAST_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "current": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "apparent_temperature",
                        "precipitation",
                        "weather_code",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "surface_pressure",
                        "visibility",
                        "uv_index",
                        "is_day",
                    ]
                ),
                "hourly": ",".join(
                    [
                        "temperature_2m",
                        "apparent_temperature",
                        "precipitation_probability",
                        "weather_code",
                        "wind_speed_10m",
                    ]
                ),
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "precipitation_sum",
                        "uv_index_max",
                        "wind_speed_10m_max",
                        "sunrise",
                        "sunset",
                    ]
                ),
                "forecast_days": 7,
                "timezone": "auto",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
        )

        current = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})
        description, icon = weather_description(current.get("weather_code"))

        hourly_items = []
        for i, timestamp in enumerate(hourly.get("time", [])):
            if len(hourly_items) >= 24:
                break
            h_code = (hourly.get("weather_code") or [None])[i]
            h_description, h_icon = weather_description(h_code)
            hourly_items.append(
                {
                    "time": timestamp,
                    "temperature_c": number((hourly.get("temperature_2m") or [None])[i]),
                    "feels_like_c": number((hourly.get("apparent_temperature") or [None])[i]),
                    "rain_probability": number((hourly.get("precipitation_probability") or [None])[i]),
                    "wind_speed": number((hourly.get("wind_speed_10m") or [None])[i]),
                    "weather_code": h_code,
                    "description": h_description,
                    "icon": h_icon,
                }
            )

        forecast = []
        for i, day in enumerate(daily.get("time", [])):
            d_code = (daily.get("weather_code") or [None])[i]
            d_description, d_icon = weather_description(d_code)
            forecast.append(
                {
                    "date": day,
                    "weather_code": d_code,
                    "description": d_description,
                    "icon": d_icon,
                    "max_c": number((daily.get("temperature_2m_max") or [None])[i]),
                    "min_c": number((daily.get("temperature_2m_min") or [None])[i]),
                    "rain_probability": number((daily.get("precipitation_probability_max") or [None])[i]),
                    "precipitation": number((daily.get("precipitation_sum") or [None])[i], 1),
                    "uv_index": number((daily.get("uv_index_max") or [None])[i], 1),
                    "max_wind": number((daily.get("wind_speed_10m_max") or [None])[i]),
                    "sunrise": (daily.get("sunrise") or [None])[i],
                    "sunset": (daily.get("sunset") or [None])[i],
                }
            )

        return jsonify(
            {
                "location": {"latitude": data.get("latitude"), "longitude": data.get("longitude")},
                "timezone": data.get("timezone", "UTC"),
                "elevation": data.get("elevation"),
                "current": {
                    "time": current.get("time"),
                    "temperature_c": number(current.get("temperature_2m")),
                    "feels_like_c": number(current.get("apparent_temperature")),
                    "humidity": number(current.get("relative_humidity_2m")),
                    "precipitation": number(current.get("precipitation"), 1),
                    "rain_probability": number((daily.get("precipitation_probability_max") or [0])[0]),
                    "wind_speed": number(current.get("wind_speed_10m")),
                    "wind_direction": number(current.get("wind_direction_10m")),
                    "pressure": number(current.get("surface_pressure")),
                    "visibility": number(current.get("visibility") / 1000 if current.get("visibility") is not None else None, 1),
                    "uv_index": number(current.get("uv_index"), 1),
                    "is_day": current.get("is_day", 1),
                    "weather_code": current.get("weather_code"),
                    "description": description,
                    "icon": icon,
                },
                "forecast": forecast,
                "hourly": hourly_items,
                "raw_json": data,
            }
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"Weather service unavailable: {exc}"}), 503


@app.route("/server/historical_weather")
def get_historical_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude are required."}), 400

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    try:
        data = api_get(
            ARCHIVE_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "weather_code,temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            },
        )
        daily = data.get("daily", {})
        result = []
        for i, day in enumerate(daily.get("time", [])):
            code = (daily.get("weather_code") or [None])[i]
            description, icon = weather_description(code)
            mean = (daily.get("temperature_2m_mean") or [None])[i]
            result.append(
                {
                    "date": day,
                    "temp_c": number(mean),
                    "temp_f": number(mean * 9 / 5 + 32) if mean is not None else None,
                    "temp_max_c": number((daily.get("temperature_2m_max") or [None])[i]),
                    "temp_min_c": number((daily.get("temperature_2m_min") or [None])[i]),
                    "precipitation": number((daily.get("precipitation_sum") or [None])[i], 1),
                    "weather_main": description,
                    "weather_description": description,
                    "icon": icon,
                    "weather_code": code,
                }
            )
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"error": f"Historical weather unavailable: {exc}"}), 503
