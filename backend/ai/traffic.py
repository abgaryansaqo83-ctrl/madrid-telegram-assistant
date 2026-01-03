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


def _speed_to_score(speed_kmh: float) -> int:
    """
    Переводит среднюю скорость в условную оценку пробки 0–10.
    0–2 балла — свободно, 3–5 — лёгкая загрузка,
    6–7 — плотное движение, 8–10 — сильная пробка.
    """
    if speed_kmh >= 60:
        return 1
    if speed_kmh >= 40:
        return 3
    if speed_kmh >= 25:
        return 5
    if speed_kmh >= 15:
        return 7
    if speed_kmh >= 5:
        return 8
    return 10


def _score_to_icon(score: int) -> str:
    """Возвращает цвет иконки по шкале 0–10."""
    if score <= 2:
        return "🟢"
    if score <= 4:
        return "🟡"
    if score <= 6:
        return "🟠"
    if score <= 8:
        return "🔴"
    return "🟥"


def _get_road_status(origin: str, destination: str):
    """
    Возвращает (название дороги, score 0–10) или None, если данных нет.
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

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except Exception:
        return None

    routes = data.get("routes", [])
    if not routes:
        return None

    leg = routes[0]["legs"][0]
    speed_kmh = _compute_speed_kmh(leg)
    if speed_kmh is None:
        return None

    summary = routes[0].get("summary", "")
    if not summary:
        return None

    score = _speed_to_score(speed_kmh)
    return summary, score


def madrid_morning_traffic():
    """
    Возвращает одно–два коротких сообщения о пробках на основных трассах:
    одна таблица «В ЦЕНТР», вторая — «ИЗ ЦЕНТРА».
    Формат строки:
      🟠 6/10 — M‑30 Norte → центр
    """
    routes_in = [
        ("M-30 Norte, Madrid", "Centro, Madrid", "M‑30 Norte → центр"),
        ("A-6, Madrid", "Centro, Madrid", "A‑6 → центр"),
        ("A-3, Madrid", "Centro, Madrid", "A‑3 → центр"),
        ("A-2, Madrid", "Centro, Madrid", "A‑2 → центр"),
        ("A-5, Madrid", "Centro, Madrid", "A‑5 → центр"),
        ("A-4, Madrid", "Centro, Madrid", "A‑4 → центр"),
    ]

    routes_out = [
        ("Centro, Madrid", "A-6, Madrid", "центр → A‑6"),
        ("Centro, Madrid", "A-3, Madrid", "центр → A‑3"),
        ("Centro, Madrid", "A-2, Madrid", "центр → A‑2"),
        ("Centro, Madrid", "A-5, Madrid", "центр → A‑5"),
        ("Centro, Madrid", "A-4, Madrid", "центр → A‑4"),
        ("Paseo de la Castellana, Madrid", "M-30 Norte, Madrid", "центр → M‑30 Norte"),
    ]

    lines_in: list[str] = []
    lines_out: list[str] = []

    for origin, dest, label in routes_in:
        status = _get_road_status(origin, dest)
        if not status:
            continue
        road_name, score = status
        icon = _score_to_icon(score)
        lines_in.append(f"{icon} {score}/10 — {label}")

    for origin, dest, label in routes_out:
        status = _get_road_status(origin, dest)
        if not status:
            continue
        road_name, score = status
        icon = _score_to_icon(score)
        lines_out.append(f"{icon} {score}/10 — {label}")

    messages: list[str] = []

    if lines_in:
        msg_in = "🚗 *В ЦЕНТР:*\n" + "\n".join(lines_in[:5])
        messages.append(msg_in)

    if lines_out:
        msg_out = "🚗 *ИЗ ЦЕНТРА:*\n" + "\n".join(lines_out[:5])
        messages.append(msg_out)

    return messages
