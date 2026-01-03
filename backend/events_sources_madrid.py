# backend/events_sources_madrid.py

import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

from backend.events import _get_conn as get_connection

logger = logging.getLogger(__name__)

Event = Dict[str, str]

# ==========================
#  SOURCE URL-ՆԵՐ
# ==========================

# Կինո – միայն Taquilla cartelera Madrid
TAQUILLA_CARTELERA_MADRID_URL = "https://www.taquilla.com/cartelera/madrid"

# Թատրոն / քաղաքային / ռեստորան – հիմա դատարկ placeholders,
# հետո երբ աղբյուր գտնենք, URL-ներ կմատուցենք այստեղ
THEATRE_URLS: list[str] = []
CITY_EVENT_URLS: list[str] = []
RESTAURANT_EVENT_URLS: list[str] = []


# ==========================
#  LOW-LEVEL HELPERS
# ==========================

def _http_get(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}", exc_info=True)
        return None


def _today_str() -> str:
    return datetime.now().date().isoformat()


# ==========================
#  CINEMA – TAQUILLA CARTELERA
# ==========================

def fetch_madrid_cinema_events(limit: int = 30) -> List[Event]:
    """
    Քաշում է Taquilla cartelera Madrid էջից մինչև `limit` ֆիլմեր.
    Ամեն ֆիլմի համար ընտրում է մեկ կոնկրետ կինոթատրոն Մադրիդում,
    և վերադարձնում Event dict list, պատրաստ DB-ի համար:
    """
    soup = _http_get(TAQUILLA_CARTELERA_MADRID_URL)
    if not soup:
        return []

    # 1) ֆիլմերի map՝ slug -> (title, image_url)
    movies: Dict[str, Dict[str, str]] = {}
    for img in soup.select("img.movie-list-thumb"):
        slug = (img.get("id") or "").strip()
        if not slug:
            continue
        title = (img.get("data-name") or "").strip()
        image_url = (img.get("src") or "").strip()
        if not title:
            continue
        movies[slug] = {
            "title": title,
            "image_url": image_url,
        }

    events: List[Event] = []
    seen_titles: set[str] = set()

    # 2) կինոթատրոնների list + class-երից ֆիլմերի slug-եր
    for div in soup.select("aside#movie_theater_list div.film-results__result"):
        name_tag = div.select_one(".film-results__name a")
        if not name_tag:
            continue
        cinema_name = name_tag.get_text(strip=True)

        address_tag = div.select_one("p.cine-results__info")
        cinema_address = address_tag.get_text(strip=True) if address_tag else ""

        content_div = div.select_one(".film-results__content.data-link")
        source_url = content_div.get("data-link", "").strip() if content_div else ""

        class_list = div.get("class") or []
        slugs_for_cinema: List[str] = []
        for cls in class_list:
            if cls in ("film-results__result", "disabled"):
                continue
            if cls.startswith("avatar-"):
                continue
            if cls in movies:
                slugs_for_cinema.append(cls)

        if not slugs_for_cinema:
            continue

        for slug in slugs_for_cinema:
            movie = movies.get(slug)
            if not movie:
                continue

            title = movie["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)

            ev: Event = {
                "title": title,
                "place": cinema_name,
                "time": "",                  # ժամ չունենք
                "date": _today_str(),
                "category": "cinema",
                "source_url": source_url,
                "address": cinema_address,
                "price": "",                 # գին չունենք
                "image_url": movie["image_url"],
            }
            events.append(ev)

            if len(events) >= limit:
                break

        if len(events) >= limit:
            break

    return events


# ==========================
#  ԴՐՈՒՅԱԹԱՐ ԹԱՏՐՈՆ / ՔԱՂԱՔ / ՌԵՍՏՈ
# ==========================

def fetch_madrid_theatre_events(limit: int = 20) -> List[Event]:
    # հիմա ոչինչ չի քաշում, թող լինի placeholder
    return []


def fetch_madrid_city_events(limit: int = 20) -> List[Event]:
    # placeholder մինչև նոր աղբյուր գտնենք
    return []


def fetch_madrid_restaurant_events(limit: int = 20) -> List[Event]:
    # placeholder մինչև աղբյուր գտնենք
    return []


# ==========================
#  DB WRITE HELPERS
# ==========================

def _save_event_to_db(ev: Event) -> None:
    try:
        from backend.events import _get_conn

        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO madrid_events 
                (title, place, start_time, date, category,
                 source_url, address, price, image_url)
            VALUES 
                (%s, %s, %s, %s, %s,
                 %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (
                ev.get("title", ""),
                ev.get("place", ""),
                ev.get("time", ""),
                ev.get("date", _today_str()),
                ev.get("category", ""),
                ev.get("source_url", ""),
                ev.get("address", ""),
                ev.get("price", ""),
                ev.get("image_url", ""),
            ),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Saved event: {ev.get('title')}")
    except Exception as e:
        logger.error(f"Error saving event to DB: {e}", exc_info=True)


def refresh_madrid_events_for_today() -> None:
    """
    Հիմա՝ մաքրում է այսօրվա madrid_events row-երը
    և լցնում նորերը միայն cinema (Taquilla) աղբյուրից.
    """
    today = _today_str()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM madrid_events WHERE date = %s;", (today,))
        conn.commit()
        conn.close()
        logger.info("Cleared today's madrid_events before refresh")
    except Exception as e:
        logger.error(f"Error clearing today's events: {e}", exc_info=True)

    # Cinema – Taquilla
    for ev in fetch_madrid_cinema_events(limit=30):
        _save_event_to_db(ev)

    logger.info("Refreshed madrid_events for today (cinema only)")


if __name__ == "__main__":
    refresh_madrid_events_for_today()
