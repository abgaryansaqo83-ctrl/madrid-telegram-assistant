# backend/events_sources_madrid.py
# ==========================
#  IMPORTS & TYPES
# ==========================
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

from backend.events import _get_conn as get_connection

logger = logging.getLogger(__name__)

Event = Dict[str, str]


# ==========================
#  SOURCE URL-ՆԵՐ
# ==========================

# Կինո
YELMO_FILM_URLS = [
    "https://yelmocines.es/sinopsis/vanya-encore-national-theatre-25-26",
    "https://yelmocines.es/sinopsis/the-world-of-hans-zimmer-a-new-dimension",
    "https://yelmocines.es/sinopsis/el-rey-de-reyes",
    "https://yelmocines.es/sinopsis/roofman-un-ladron-en-el-tejado",
]

ECARTELERA_FILM_URLS = [
    "https://www.ecartelera.com/peliculas/coartadas/",
    "https://www.ecartelera.com/peliculas/playa-de-lobos/",
]

TAQUILLA_FILM_URLS = [
    "https://www.taquilla.com/entradas/ahora-me-ves-3",
    "https://www.taquilla.com/entradas/la-voz-de-hind",
    "https://www.taquilla.com/madrid/yelmo-cines-ideal-madrid",
]

# Թատրոն
THEATRE_URLS = [
    "https://teatromadrid.com/espectaculo/un-dios-salvaje?funcio_id=278142",
    "https://teatromadrid.com/espectaculo/victoria-2",
    "https://teatromadrid.com/espectaculo/corta-cable-rojo",
    "https://teatromadrid.com/espectaculo/josema-yuste-que-dios-nos-pille-confesados",
    "https://madridesteatro.com/un-dios-salvaje-en-el-teatro-alcazar/",
]

# Քաղաքային / տոնական միջոցառումներ
CITY_EVENT_URLS = [
    "https://www.esmadrid.com/agenda-navidad-madrid",
    "https://www.esmadrid.com/calendario-eventos-madrid",
    "https://www.esmadrid.com/agenda/circo-price-navidad-teatro-circo-price",
    "https://www.navidadmadrid.com/es/evento/mercado-navideno-plaza-mayor-de-madrid",
    "https://dondego.es/madrid/event/feria-mercado-de-navidad-de-la-plaza-mayor/",
    "https://dondego.es/madrid/event/espectculo-droneart-show-enero-2026/",
]

# Ռեստորաններ / bar / club event-ներ
RESTAURANT_EVENT_URLS = [
    "https://www.eventoplus.com/espacios/bule-bule/",
    "https://www.eventoplus.com/espacios/florida-park/",
    "https://www.eventoplus.com/espacios/unas-chung-lee/",
    "https://www.eventoplus.com/espacios/fitz-club-madrid/",
]


# ==========================
#  LOW-LEVEL HELPERS
# ==========================

def _http_get(url: str) -> Optional[BeautifulSoup]:
    """
    Պարզ GET helper, որը վերադարձնում է BeautifulSoup կամ None:
    Հետագայում այստեղ կարելի է ավելացնել headers, retry և այլն.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}", exc_info=True)
        return None


def _today_str() -> str:
    """Այսօրվա ամսաթիվը ISO (YYYY-MM-DD) ձևաչափով՝ DB-ի համար."""
    return datetime.now().date().isoformat()


# ==========================
#  SCRAPER PLACEHOLDERS
# ==========================
# Հիմա scrapers-ը շատ պարզ են՝ միայն title + source/url.
# Հետագայում կարող ենք ավելացնել իրական parsing (date/time/place/price):

def _scrape_yelmo_film(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    # Title-ը սովորաբար h1 tag-ում է
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Sin título"

    return {
        "title": title,
        "place": "Yelmo Cines (Madrid)",
        "time": "",               # հետո կլրացնենք իրական սեսիաներով
        "date": _today_str(),     # հիմա՝ որպես placeholder, այսօր
        "category": "cinema",
        "source_url": url,
    }


def _scrape_ecartelera_film(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Sin título"

    return {
        "title": title,
        "place": "Cines de Madrid",
        "time": "",
        "date": _today_str(),
        "category": "cinema",
        "source_url": url,
    }


def _scrape_taquilla_film(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Sin título"

    return {
        "title": title,
        "place": "Cines / Teatros (Taquilla)",
        "time": "",
        "date": _today_str(),
        "category": "cinema",
        "source_url": url,
    }


def _scrape_theatre_event(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Sin título"

    return {
        "title": title,
        "place": "Teatros de Madrid",
        "time": "",
        "date": _today_str(),
        "category": "theatre",
        "source_url": url,
    }


def _scrape_city_event(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Evento en Madrid"

    return {
        "title": title,
        "place": "Madrid",
        "time": "",
        "date": _today_str(),
        "category": "holiday",  # կամ "city_event"
        "source_url": url,
    }


def _scrape_restaurant_event(url: str) -> Optional[Event]:
    soup = _http_get(url)
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Evento gastronómico"

    return {
        "title": title,
        "place": "Restaurante / Club en Madrid",
        "time": "",
        "date": _today_str(),
        "category": "restaurant",
        "source_url": url,
    }


# ==========================
#  PUBLIC FETCH FUNCTIONS
# ==========================

def fetch_madrid_cinema_events(limit: int = 20) -> List[Event]:
    """
    Քաշում է մի քանի կինո event տարբեր աղբյուրներից և վերադարձնում list[Event].
    Հիմա՝  շատ պարզ՝ per-URL scraping h1 title-ով:
    """
    events: List[Event] = []

    for url in YELMO_FILM_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_yelmo_film(url)
        if ev:
            events.append(ev)

    for url in ECARTELERA_FILM_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_ecartelera_film(url)
        if ev:
            events.append(ev)

    for url in TAQUILLA_FILM_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_taquilla_film(url)
        if ev:
            events.append(ev)

    return events[:limit]


def fetch_madrid_theatre_events(limit: int = 20) -> List[Event]:
    events: List[Event] = []
    for url in THEATRE_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_theatre_event(url)
        if ev:
            events.append(ev)
    return events[:limit]


def fetch_madrid_city_events(limit: int = 20) -> List[Event]:
    events: List[Event] = []
    for url in CITY_EVENT_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_city_event(url)
        if ev:
            events.append(ev)
    return events[:limit]


def fetch_madrid_restaurant_events(limit: int = 20) -> List[Event]:
    events: List[Event] = []
    for url in RESTAURANT_EVENT_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_restaurant_event(url)
        if ev:
            events.append(ev)
    return events[:limit]


# ==========================
#  DB WRITE HELPERS (madrid_events)
# ==========================

def _save_event_to_db(ev: Event) -> None:
    """
    Գրանցում է event-ը madrid_events աղյուսակում՝
    ՈՒՂՂԱԿԻ SQL INSERT-ով (առանց upsert_event()).
    """
    try:
        from backend.events import _get_conn
        
        conn = _get_conn()
        cur = conn.cursor()
        
        # Պարզ INSERT
        cur.execute(
            """
            INSERT INTO madrid_events 
                (title, place, start_time, date, category, source_url)
            VALUES 
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (
                ev.get("title", ""),
                ev.get("place", ""),
                ev.get("time", ""),
                ev.get("date", _today_str()),
                ev.get("category", ""),
                ev.get("source_url", ""),
            ),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Saved event: {ev.get('title')}")
    except Exception as e:
        logger.error(f"Error saving event to DB: {e}", exc_info=True)


def refresh_madrid_events_for_today() -> None:
    """
    Գիշերային job-ի համար.
    Մաքրում է այսօրվա madrid_events row-երը և լցնում նորերը
    տարբեր աղբյուրներից (cinema / theatre / restaurant / city events).
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

    # Cinema
    for ev in fetch_madrid_cinema_events(limit=10):
        _save_event_to_db(ev)

    # Theatre
    for ev in fetch_madrid_theatre_events(limit=10):
        _save_event_to_db(ev)

    # Restaurant / bar events
    for ev in fetch_madrid_restaurant_events(limit=10):
        _save_event_to_db(ev)

    # City / holiday events
    for ev in fetch_madrid_city_events(limit=10):
        _save_event_to_db(ev)

    logger.info("Refreshed madrid_events for today")


if __name__ == "__main__":
    # Մանուալ запуск Web Shell-ից
    refresh_madrid_events_for_today()
