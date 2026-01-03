# backend/news.py

# ==========================
#  IMPORTS & TYPES
# ==========================
import logging
from typing import List, Dict

from .events import (
    get_upcoming_theatre_events,
    get_upcoming_cinema_events,
    get_upcoming_restaurant_events,
    get_upcoming_holiday_events,
)

logger = logging.getLogger(__name__)

Event = Dict[str, str]


# ==========================
#  HELPERS
# ==========================
def _format_event_line(event: Event, icon: str = "🎫") -> str:
    """
    Ֆորմատավորում է մեկ event card-ի տեսքով (առանց նկարների).
    Կկարտա.
      🎫 Title
      📍 Place
      🕐 Time
      🔗 URL (եթե կա)
    """
    title = (event.get("title") or "").strip() or "Без названия"
    place = (event.get("place") or "").strip()
    time = (event.get("time") or "").strip()
    url = (event.get("url") or "").strip()

    lines: List[str] = []
    lines.append(f"{icon} *{title}*")

    if place:
        lines.append(f"📍 {place}")

    if time:
        lines.append(f"🕐 {time}")

    if url:
        lines.append(f"🔗 [Подробнее]({url})")

    return "\n".join(lines)


def _build_block(
    title_line: str,
    events: List[Event],
    icon: str,
    max_items: int,
) -> str:
    """
    Ընդհանուր helper՝ կառուցում է block մեկ կատեգորիայի համար.
    Վերցնում է մինչև max_items event և վերադարձնում է Markdown-ready text.
    """
    if not events:
        return ""

    # Վերցնենք միայն առաջին N event-ները
    limited = events[:max_items]

    lines: List[str] = []
    lines.append(title_line)
    lines.append("")  # դատարկ տող header-ից հետո

    for ev in limited:
        lines.append(_format_event_line(ev, icon=icon))
        lines.append("")  # դատարկ տող event-ների միջև

    # Հեռացնում ենք վերջի դատարկ տողը, եթե կա
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


# ==========================
# 1) ОБЗОР ГОРОДА
# ==========================
def build_city_overview_message() -> str:
    return ""

# ==========================
# 2) КИНО / РАЗВЛЕЧЕНИЯ
# ==========================
def build_cinema_message(max_items: int = 2) -> str:
    """
    🎬 Кино и развлечения
    Берём до max_items ближайших событий категории 'cinema'.
    """
    try:
        events = get_upcoming_cinema_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building cinema message: {e}", exc_info=True)
        return ""

    return _build_block(
        title_line="🎬 *Кино и развлечения:*",
        events=events,
        icon="🎬",
        max_items=max_items,
    )


# ==========================
# 3) СОБЫТИЯ В РЕСТОРАНАХ
# ==========================
def build_restaurant_message(max_items: int = 2) -> str:
    """
    🍽 События в ресторанах и барах
    Берём до max_items событий категории 'restaurant'.
    """
    try:
        events = get_upcoming_restaurant_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building restaurant message: {e}", exc_info=True)
        return ""

    return _build_block(
        title_line="🍷 *Бары и рестораны:*",
        events=events,
        icon="🍷",
        max_items=max_items,
    )


# ==========================
# 4) ПРАЗДНИКИ / ГОРОДСКИЕ МЕРОПРИЯТИЯ
# ==========================
def build_holidays_message(max_items: int = 2) -> str:
    """
    🎉 Праздники и городские мероприятия
    Универсальный блок для Рождества, НГ и городских праздников.
    """
    try:
        events = get_upcoming_holiday_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building holidays message: {e}", exc_info=True)
        return ""

    return _build_block(
        title_line="🎉 *Городские мероприятия и праздники:*",
        events=events,
        icon="🎉",
        max_items=max_items,
    )


# ==========================
# 5) ТЕАТР И СЦЕНА МАДРИДА
# ==========================
def build_theatre_message(max_items: int = 2) -> str:
    """
    🎭 Театр и сцена Мадрида
    Берём до max_items ближайших событий категории 'theatre'.
    """
    try:
        events = get_upcoming_theatre_events(limit=max_items)
    except Exception as e:
        logger.error(f"Error building theatre message: {e}", exc_info=True)
        return ""

    return _build_block(
        title_line="🎭 *Театр и сцена Мадрида:*",
        events=events,
        icon="🎭",
        max_items=max_items,
    )
