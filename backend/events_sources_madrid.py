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

ECARTELERA_FILM_URLS = [
    "https://www.ecartelera.com/peliculas/coartadas/",
    "https://www.ecartelera.com/peliculas/playa-de-lobos/",
]

TAQUILLA_CARTELERA_MADRID_URL = "https://www.taquilla.com/cartelera/madrid"

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

def fetch_madrid_cinema_events(limit: int = 30) -> List[Event]:
    """
    Քաշում է Taquilla cartelera Madrid էջից մինչև `limit` ֆիլմեր.
    Ամեն ֆիլմի համար ընտրում է random մեկ կինոթատրոն Մադրիդում
    և վերադարձնում Event dict list, պատրաստ DB-ի համար:
    """
    soup = _http_get(TAQUILLA_CARTELERA_MADRID_URL)
    if not soup:
        return []

    # 1) Ֆիլմերի map՝ slug -> (title, image_url)
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

    # 2) Կինոթատրոնների list + որ ֆիլմերն են գնում այնտեղ
    #    div.film-results__result – չդիտարկենք որոնք "SIN ENTRADAS" ունեն, եթե չես ուզում
    events: List[Event] = []
    seen_titles: set[str] = set()

    for div in soup.select("aside#movie_theater_list div.film-results__result"):
        # cinema basic info
        name_tag = div.select_one(".film-results__name a")
        if not name_tag:
            continue
        cinema_name = name_tag.get_text(strip=True)

        address_tag = div.select_one("p.cine-results__info")
        cinema_address = address_tag.get_text(strip=True) if address_tag else ""

        content_div = div.select_one(".film-results__content.data-link")
        source_url = content_div.get("data-link", "").strip() if content_div else ""

        # class-երից հավաքում ենք ֆիլմերի slug-երը
        class_list = div.get("class") or []
        slugs_for_cinema: List[str] = []
        for cls in class_list:
            if cls in ("film-results__result", "disabled"):
                continue
            if cls.startswith("avatar-"):
                continue
            # մնացած class-երը ֆիլմերի slug-երն են
            if cls in movies:
                slugs_for_cinema.append(cls)

        if not slugs_for_cinema:
            continue

        # Յուրաքանչյուր ֆիլմի համար կարող ենք սարքել event,
        # բայց limit պահելու համար կկտրենք ավելի ուշ
        for slug in slugs_for_cinema:
            movie = movies.get(slug)
            if not movie:
                continue

            title = movie["title"]

            # Եթե ուզում ես մեկ անգամ միայն յուրաքանչյուր title-ը,
            # ապա կարող ենք skip անել արդեն տեսած վերնագրերը
            if title in seen_titles:
                continue
            seen_titles.add(title)

            ev: Event = {
                "title": title,
                "place": cinema_name,
                "time": "",                     # ժամեր չունենք
                "date": _today_str(),           # կամ ավելի ուշ cities_dates-ից real օր դնես
                "category": "cinema",
                "source_url": source_url,
                "address": cinema_address,
                "price": "",                    # գին էլ հիմա չունենք
                "image_url": movie["image_url"],
            }
            events.append(ev)

            if len(events) >= limit:
                break

        if len(events) >= limit:
            break

    return events


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
    for ev in fetch_madrid_cinema_events(limit=30):
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
