# backend/news.py
# ==========================
#  IMPORTS & TYPES
# ==========================
import logging
from typing import List, Dict

from .events import (
    get_upcoming_cinema_events,
    get_upcoming_restaurant_events,
    get_upcoming_holiday_events,
)

logger = logging.getLogger(__name__)

Event = Dict[str, str]


# ==========================
#  HELPERS
# ==========================
def _format_event_line(event: Event) -> str:
    """
    Формирует одну строку вида:
    • Название — место — дата/время
    """
    title = (event.get("title") or "").strip() or "Без названия"
    place = (event.get("place") or "").strip()
    time = (event.get("time") or "").strip()

    parts: List[str] = [title]
    if place:
        parts.append(place)
    if time:
        parts.append(time)

    return "• " + " — ".join(parts)


# ==========================
# 1) ОБЗОР ГОРОДА
# ==========================
def build_city_overview_message() -> str:
    """
    Краткий обзор «что сегодня происходит в Мадриде».
    Все формулировки — на русском, без конкретных адресов и цен.
    """
    try:
        cinema_events = get_upcoming_cinema_events(limit=5)
        rest_events = get_upcoming_restaurant_events(limit=5)
        holiday_events = get_upcoming_holiday_events(limit=5)
    except Exception as e:
        logger.error(f"Error building city overview: {e}", exc_info=True)
        return ""

    if not (cinema_events or rest_events or holiday_events):
        return ""

    lines: List[str] = []
    lines.append("🌆 Обзор дня в Мадриде:")

    if cinema_events:
        lines.append(
            "🎬 Сегодня проходят показы фильмов и спектаклей "
            "в нескольких кинотеатрах и театрах города."
        )
    if rest_events:
        lines.append(
            "🍽 В барах и ресторанах — тематические вечера, живая музыка и специальные меню."
        )
    if holiday_events:
        lines.append(
            "🎉 По городу проходят праздничные мероприятия: ярмарки, концерты и программы для детей."
        )

    lines.append("")
    lines.append(
        "ℹ️ Подробности по отдельным событиям смотрите ниже "
        "в блоках про кино, рестораны и праздники."
    )

    return "\n".join(lines)


# ==========================
# 2) КИНО / РАЗВЛЕЧЕНИЯ
# ==========================
def build_cinema_message(max_items: int = 3) -> str:
    """
    🎬 Кино и развлечения
    Берём до max_items ближайших событий категории 'cinema'.
    """
    try:
        events = get_upcoming_cinema_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building cinema message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines: List[str] = []
    lines.append("🎬 Кино и развлечения:")

    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


# ==========================
# 3) СОБЫТИЯ В РЕСТОРАНАХ
# ==========================
def build_restaurant_message(max_items: int = 3) -> str:
    """
    🍽 События в ресторанах
    Берём до max_items событий категории 'restaurant'.
    """
    try:
        events = get_upcoming_restaurant_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building restaurant message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines: List[str] = []
    lines.append("🍽 События в ресторанах:")

    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


# ==========================
# 4) ПРАЗДНИКИ / ГОРОДСКИЕ МЕРОПРИЯТИЯ
# ==========================
def build_holidays_message(max_items: int = 3) -> str:
    """
    🎉 Праздники в Мадриде
    Универсальный блок для Рождества, НГ и городских праздников.
    """
    try:
        events = get_upcoming_holiday_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building holidays message: {e}", exc_info=True)
        return ""

    if not events:
        return ""

    lines: List[str] = []
    lines.append("🎉 Праздники в Мадриде:")

    for ev in events:
        lines.append(_format_event_line(ev))

    return "\n".join(lines)


# ==========================
# 5) УТРЕННИЙ ДАЙДЖЕСТ
# ==========================
def build_morning_event_messages(
    max_cinema: int = 3,
    max_restaurants: int = 3,
    max_holidays: int = 3,
) -> List[str]:
    """
    Возвращает список текстов для утреннего дайджеста.
    Каждый элемент списка — отдельное сообщение.
    Используется scheduler.py для отправки в группу.
    """
    messages: List[str] = []

    overview = build_city_overview_message()
    if overview:
        messages.append(overview)

    cinema = build_cinema_message(max_items=max_cinema)
    if cinema:
        messages.append(cinema)

    restaurants = build_restaurant_message(max_items=max_restaurants)
    if restaurants:
        messages.append(restaurants)

    holidays = build_holidays_message(max_items=max_holidays)
    if holidays:
        messages.append(holidays)

    return messages
