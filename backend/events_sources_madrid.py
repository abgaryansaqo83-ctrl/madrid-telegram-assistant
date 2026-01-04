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
TAQUILLA_THEATRE_LIST_URL = "https://www.taquilla.com/espectaculos/teatro/madrid"

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

def _parse_taquilla_date(date_str: str) -> str:
    """
    '04 Ene' տեսակի օրերից ISO 'YYYY-MM-DD' կառուցելու helper,
    fallback՝ այսօր, եթե չստացվեր parse անել։
    """
    date_str = date_str.strip()
    # Taquilla already gives ISO in meta[startDate], so this is fallback only
    try:
        # Օրինակ '2026-01-04'
        dt = datetime.fromisoformat(date_str)
        return dt.date().isoformat()
    except Exception:
        return _today_str()


def fetch_taquilla_theatre_events_from_list(url: str, limit: int = 20) -> List[Event]:
    """
    Քաշում է theatre event-ներ Taquilla theatre list էջից
    (https://www.taquilla.com/espectaculos/teatro/madrid).

    Վերցնում ենք.
      - title
      - theatre/place
      - address
      - date (startDate)
      - time (առաջին ցուցված ժամ)
      - price (lowPrice կամ «desde X,00€» տեքստը)
      - image_url
      - source_url
    """
    soup = _http_get(url)
    if not soup:
        return []

    events: List[Event] = []

    # Յուրաքանչյուր event գալիս է որպես <li itemscope itemtype="https://schema.org/TheaterEvent">
    for li in soup.find_all("li", itemtype="https://schema.org/TheaterEvent"):
        if len(events) >= limit:
            break

        # Title
        name_meta = li.find("meta", itemprop="name")
        title = name_meta["content"].strip() if name_meta and name_meta.has_attr("content") else "Sin título"

        # Source URL (event URL)
        url_meta = li.find("meta", itemprop="url")
        source_url = url_meta["content"].strip() if url_meta and url_meta.has_attr("content") else url

        # Image
        img_meta = li.find("meta", itemprop="image")
        image_url = img_meta["content"].strip() if img_meta and img_meta.has_attr("content") else ""

        # Location / theatre name
        location = li.find(attrs={"itemprop": "location"})
        place = ""
        address = ""
        if location:
            loc_name = location.find("meta", itemprop="name")
            if loc_name and loc_name.has_attr("content"):
                place = loc_name["content"].strip()

            addr = location.find(attrs={"itemprop": "address"})
            if addr:
                street = addr.find("meta", itemprop="streetAddress")
                if street and street.has_attr("content"):
                    address = street["content"].strip()

        # Date (startDate)
        date_meta = li.find("meta", itemprop="startDate")
        date_iso = _today_str()
        if date_meta and date_meta.has_attr("content"):
            date_iso = _parse_taquilla_date(date_meta["content"])

        # Time (առաջին ժամից)
        time_div = li.select_one(".ent-results-list-hour-time span")
        start_time = time_div.get_text(strip=True) if time_div else ""

        # Price
        price_text = ""
        price_meta = li.find("meta", itemprop="lowPrice")
        if price_meta and price_meta.has_attr("content"):
            price_text = f"{price_meta['content']}€"
        else:
            price_span = li.select_one(".ent-results-list-hour-price span")
            if price_span:
                price_text = price_span.get_text(strip=True)

        ev: Event = {
            "title": title,
            "place": place or "Teatro en Madrid",
            "time": start_time,
            "date": date_iso,
            "category": "theatre",
            "source_url": source_url,
            # optional extra fields if DB later supports them
            "image_url": image_url,
            "address": address,
            "price": price_text,
        }

        events.append(ev)

    return events

# ==========================
#  ԴՐՈՒՅԱԹԱՐ ԹԱՏՐՈՆ / ՔԱՂԱՔ / ՌԵՍՏՈ
# ==========================

def fetch_madrid_theatre_events(limit: int = 20) -> List[Event]:
    events: List[Event] = []

    # 1) Taquilla theatre list (ամենահարստացված տվյալները՝ նկար, ժամ, գին)
    taquilla_events = fetch_taquilla_theatre_events_from_list(
        TAQUILLA_THEATRE_LIST_URL, limit=limit
    )
    events.extend(taquilla_events)

    # 2) Քո հին THEATRE_URLS աղբյուրները՝ եթե դեռ տեղ կա
    for url in THEATRE_URLS:
        if len(events) >= limit:
            break
        ev = _scrape_theatre_event(url)
        if ev:
            events.append(ev)

    return events[:limit]


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

        today = _today_str()  # 👈 ֆիքսված այսօր

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
                today,                      # 👈 էստեղ այլևս ev["date"] չենք օգտագործում
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
    Ամեն գիշեր.
    - Ջնջում է մինչև այսօրը ներառյալ նախորդ օրերի events-ները.
    - Քաշում է այսօրվա համար նոր events (cinema, հետո theatre/restaurants...):
    """
    today = _today_str()
    try:
        conn = get_connection()
        cur = conn.cursor()
        # ջնջենք միայն նախորդ օրերը, այսօրը և ապագան թողնենք
        cur.execute("DELETE FROM madrid_events WHERE date < %s;", (today,))
        conn.commit()
        conn.close()
        logger.info("Cleared past madrid_events before refresh")
    except Exception as e:
        logger.error(f"Error clearing past events: {e}", exc_info=True)

    # Cinema – Taquilla (միայն այսօր)
    for ev in fetch_madrid_cinema_events(limit=30):
        _save_event_to_db(ev)

    logger.info("Refreshed madrid_events for today (cinema only)")

if __name__ == "__main__":
    refresh_madrid_events_for_today()
