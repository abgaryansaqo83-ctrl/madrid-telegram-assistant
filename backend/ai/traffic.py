import os
import requests

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "AIzaSyCv2Pum7Uv-EZ2Mocn_RGuwV5qE7cioC-w"

def get_traffic_status(origin, destination):
    """
    Возвращает дорожную ситуацию от origin до destination.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_API_KEY,
        "departure_time": "now",
        "region": "es",
        "mode": "driving"
    }
    response = requests.get(url, params=params)
    data = response.json()
    routes = data.get("routes", [])
    if not routes:
        return "Нет данных о дорожной ситуации по этому маршруту."

    leg = routes[0]["legs"][0]
    start = leg["start_address"]
    end = leg["end_address"]
    duration = leg.get("duration", {}).get("text", "")
    duration_in_traffic = leg.get("duration_in_traffic", {}).get("text", duration)
    distance = leg.get("distance", {}).get("text", "")
    summary = routes[0].get("summary", "")

    return (
        f"📍 Маршрут: {start} → {end}\n"
        f"⏱️ Среднее время: {duration}\n"
        f"⚠️ С учётом пробок: {duration_in_traffic}\n"
        f"🛣️ Расстояние: {distance}\n"
        f"🛤️ Основная дорога: {summary}"
    )

def madrid_morning_traffic():
    """
    Возвращает дорожную ситуацию для основных маршрутов в Мадриде утром.
    """
    routes = [
        ("Las Tablas, Madrid", "Plaza de Castilla, Madrid"),
        ("Sanchinarro, Madrid", "Plaza de Castilla, Madrid"),
        ("Fuencarral, Madrid", "Plaza de Castilla, Madrid"),
        ("Plaza de Castilla, Madrid", "Alcobendas, Madrid"),
        ("Chamartín, Madrid", "Centro, Madrid"),
    ]
    reports = []
    for origin, dest in routes:
        reports.append(get_traffic_status(origin, dest))
    return "\n\n".join(reports)
