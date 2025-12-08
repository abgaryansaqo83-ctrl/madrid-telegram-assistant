# backend/news.py

import logging
from typing import List, Dict

from .events import (
    get_upcoming_cinema_events,
    get_upcoming_restaurant_events,
    get_upcoming_holiday_events,
)

logger = logging.getLogger(__name__)

Event = Dict[str, str]


def _format_event_line(event: Event) -> str:
    """
    event -> '• Название — место, время'
    """
    title = event.get("title", "Без названия")
    place = event.get("place", "").strip()
    time = event.get("time", "").strip()

    parts: List[str] = [title]
    if place:
        parts.append(place)
    if time:
        parts.append(time)

    return "• " + " — ".join(parts)


def build_cinema_message(max_items: int = 3) -> str:
    """
    🎬 Кино и развлечения
    Возвращает готовый текст или пустую строку, если событий нет.
    """
    try:
        events = get_upcoming_cinema_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building cinema message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines = ["🎬 Кино и развлечения:"]
    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


def build_restaurant_message(max_items: int = 3) -> str:
    """
    🍽 События в ресторанах
    """
    try:
        events = get_upcoming_restaurant_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building restaurant message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines = ["🍽 События в ресторанах:"]
    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


def build_holidays_message(max_items: int = 3) -> str:
    """
    🎉 Праздники в Мадриде
    Универсальный блок для Рождества, НГ и других городских праздников.
    """
    try:
        events = get_upcoming_holiday_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building holidays message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines = ["🎉 Праздники в Мадриде:"]
    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


def build_morning_event_messages() -> List[str]:
    """
    Собирает до 3 коротких сообщений для утренней рассылки.
    Политических новостей здесь нет – только события.
    """
    messages: List[str] = []

    cinema_text = build_cinema_message()
    if cinema_text:
        messages.append(cinema_text)

    rest_text = build_restaurant_message()
    if rest_text:
        messages.append(rest_text)

    holidays_text = build_holidays_message()
    if holidays_text:
        messages.append(holidays_text)

    return messages
