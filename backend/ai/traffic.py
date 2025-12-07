import os
import requests

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "CHANGE_ME"


def _compute_speed_kmh(leg) -> float | None:
    """Возвращает среднюю скорость по участку в км/ч или None, если данных нет."""
    distance_m = leg.get("distance", {}).get("value")
    duration_in_traffic_s = leg.get("duration_in_traffic", {}).get("value") or leg.get(
        "duration", {}
    ).get("value")

    if not distance_m or not duration_in_traffic_s:
        return None

    hours = duration_in_traffic_s / 3600
    if hours <= 0:
        return None

    return (distance_m / 1000) / hours


def _get_congested_road(origin: str, destination: str, speed_threshold_kmh: float = 10.0):
    """
    Если по маршруту есть сильная пробка (скорость <= speed_threshold_kmh),
    возвращает название основной дороги (summary), иначе None.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_API_KEY,
        "departure_time": "now",
        "region": "es",
        "mode": "driving",
    }

    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()

    routes = data.get("routes", [])
    if not routes:
        return None

    leg = routes[0]["legs"][0]
    speed_kmh = _compute_speed_kmh(leg)
    if speed_kmh is None:
        return None

    if speed_kmh > speed_threshold_kmh:
        # Едем быстрее 10 км/ч — считаем, что пробка не критичная
        return None

    summary = routes[0].get("summary", "")
    if not summary:
        return None

    return summary


def madrid_morning_traffic():
    """
    Формирует до двух коротких сообщений о пробках:
    одно «В ЦЕНТР», второе «ОТ ЦЕНТРА».
    Возвращает список непустых строк (0–2 элементов).
    """
    # Примеры направлений — замени/расширь под реальные ключевые трассы Мадрида.
    routes_in = [
        # В центр
        ("M-30 Norte, Madrid", "Centro, Madrid"),
        ("A-6, Madrid", "Paseo de la Castellana, Madrid"),
        ("A-3, Madrid", "Centro, Madrid"),
        ("A-2, Madrid", "Centro, Madrid"),
        ("A-5, Madrid", "Centro, Madrid"),
        ("A-4, Madrid", "Centro, Madrid"),
    ]

    routes_out = [
        # От центра
        ("Centro, Madrid", "A-6, Madrid"),
        ("Centro, Madrid", "A-3, Madrid"),
        ("Centro, Madrid", "A-2, Madrid"),
        ("Centro, Madrid", "A-5, Madrid"),
        ("Centro, Madrid", "A-4, Madrid"),
        ("Paseo de la Castellana, Madrid", "M-30 Norte, Madrid"),
    ]

    congested_in: set[str] = set()
    congested_out: set[str] = set()

    for origin, dest in routes_in:
        road = _get_congested_road(origin, dest)
        if road:
            congested_in.add(road)

    for origin, dest in routes_out:
        road = _get_congested_road(origin, dest)
        if road:
            congested_out.add(road)

    messages: list[str] = []

    if congested_in:
        roads = ", ".join(sorted(congested_in))
        messages.append(
            "🚗 В ЦЕНТР:\n"
            f"Сегодня сильные пробки на: {roads}. Рекомендуем по возможности объезжать."
        )

    if congested_out:
        roads = ", ".join(sorted(congested_out))
        messages.append(
            "🚗 ОТ ЦЕНТРА:\n"
            f"Сегодня сильные пробки на: {roads}. Рекомендуем по возможности объезжать."
        )

    return messages
