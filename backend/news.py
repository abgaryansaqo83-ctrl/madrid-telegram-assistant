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


# ============================ Общие helpers ============================

def _format_event_line(event: Event) -> str:
    """
    Формирует одну строку вида:
    • Название (как есть из источника) — место, 10.12 19:30
    """
    # Название и остальные поля не переводим, берем как есть
    title = (event.get("title") or "").strip() or "Без названия"
    place = (event.get("place") or "").strip()
    time = (event.get("time") or "").strip()

    parts: List[str] = [title]
    if place:
        parts.append(place)
    if time:
        parts.append(time)

    return "• " + " — ".join(parts)


# ====================== 1. Обзор города (overview) =====================

def build_city_overview_message() -> str:
    """
    Краткий обзор «что сегодня происходит в Мадриде».
    Здесь даем только обобщённое описание, без конкретных адресов и цен.
    Все формулировки — на русском.
    """
    try:
        cinema_events = get_upcoming_cinema_events(limit=5)
        rest_events = get_upcoming_restaurant_events(limit=5)
        holiday_events = get_upcoming_holiday_events(limit=5)
    except Exception as e:
        logger.error(f"Error building city overview: {e}", exc_info=True)
        return ""

    # Если совсем ничего нет, просто не отправляем этот блок
    if not (cinema_events or rest_events or holiday_events):
        return ""

    lines: List[str] = []
    lines.append("🌆 Обзор дня в Мадриде:")

    # Кино и театр
    if cinema_events:
        lines.append("🎬 Сегодня проходят показы фильмов и спектаклей в нескольких кинотеатрах и театрах города.")
    # Рестораны
    if rest_events:
        lines.append("🍽 В ряде баров и ресторанов — тематические вечера, живая музыка и специальные меню.")
    # Праздники / городские мероприятия
    if holiday_events:
        lines.append("🎉 По городу проходят праздничные мероприятия: ярмарки, концерты и программы для детей.")

    lines.append("")
    lines.append("ℹ️ Подробности по отдельным событиям смотрите ниже в блоках про кино, рестораны и праздники.")

    return "\n".join(lines)


# ===================== 2. Кино и развлечения ===========================

def build_cinema_message(max_items: int = 3) -> str:
    """
    🎬 Кино и развлечения
    Берём до max_items ближайших событий категории 'cinema'
    и выводим их как есть, без перевода заголовков.
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


# ===================== 3. События в ресторанах =========================

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


# ===================== 4. Праздники в Мадриде ==========================

def build_holidays_message(max_items: int = 3) -> str:
    """
    🎉 Праздники в Мадриде
    Универсальный блок для Рождества, Нового года и других городских праздников.
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


# ==============
