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

# 🎬 Կինո – Taquilla cartelera Madrid
TAQUILLA_CARTELERA_MADRID_URL = "https://www.taquilla.com/cartelera/madrid"

# 🎭 Շոու / թատրոն / մյուզիքլ / և այլն — Taquilla espectáculos en Madrid
TAQUILLA_SHOW_CATEGORIES = {
    "theatre": "https://www.taquilla.com/espectaculos/teatro/madrid",
    "musical": "https://www.taquilla.com/espectaculos/musicales/madrid",
    "comedy": "https://www.taquilla.com/espectaculos/humor-monologos/madrid",
    "magic": "https://www.taquilla.com/espectaculos/magia/madrid",
    "kids": "https://www.taquilla.com/espectaculos/ninos/madrid",
    "circo": "https://www.taquilla.com/espectaculos/circo/madrid",
    "flamenco": "https://www.taquilla.com/espectaculos/flamenco/madrid",
    "opera": "https://www.taquilla.com/espectaculos/clasica/madrid",
    "dance": "https://www.taquilla.com/espectaculos/danza/madrid",
    "other": "https://www.taquilla.com/espectaculos/otros-espectaculos/madrid",
}

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
#  TAQUILLA MOSAIC SHOW PAGES
# ==========================

def _parse_taquilla_mosaic_date_range(date_text: str) -> str:
    """
    Mosaic картերում օրը գալիս է որպես:
      'Del <span>01-03-2026</span> al <span>04-01-2026</span>'
    Վերադարձնում է start date ISO-ով (YYYY-MM-DD) կամ այսօր:
    """
    try:
        parts = date_text.split()
        for p in parts:
            if "-" in p and len(p) == 10:
                day, month, year = p.split("-")
                dt = datetime(int(year), int(month), int(day))
                return dt.date().isoformat()
    except Exception:
        pass
    return _today_str()


def fetch_taquilla_show_category(url: str, category_slug: str, limit: int = 20) -> List[Event]:
    """
    Քաշում է մինչև `limit` շոու Taquilla-ի որևէ «espectaculos/.../madrid» էջից
    (Musicales, Teatro, Ninos, Circo, Flamenco և այլն):
      - title
      - date (սկզբի օր)
      - place (եթե կա)
      - price (Desde X,00€)
      - image_url
      - source_url
    """
    soup = _http_get(url)
    if not soup:
        return []

    events: List[Event] = []

    for box in soup.select("div.d-mosaic__box"):
        if len(events) >= limit:
            break

        # Նկար
        img = box.select_one(".d-mosaic__thumb img.d-mosaic__img")
        image_url = (img.get("data-src") or img.get("src") or "").strip() if img else ""

        # Վերնագիր + event URL
        title_tag = box.select_one("h3.d-mosaic__title a.anchor-text")
        title = ""
        source_url = ""
        if title_tag:
            # Տեքստը գալիս է "<span>Entradas</span>Название"
            title = title_tag.get_text(strip=True).replace("Entradas", "").strip()
            href = title_tag.get("href") or ""
            if href and href.startswith("/"):
                source_url = "https://www.taquilla.com" + href
            else:
                source_url = href.strip()

        # Քաղաք / place (եթե նշված է)
        place = ""
        tag_city = box.select_one(".d-mosaic__tags span")
        if tag_city:
            place = tag_city.get_text(strip=True)

        # Ամսաթիվ range
        date_div = box.select_one(".d-mosaic__date")
        date_iso = _today_str()
        if date_div:
            date_iso = _parse_taquilla_mosaic_date_range(
                date_div.get_text(" ", strip=True)
            )

        # Գին
        price_div = box.select_one(".d-mosaic__c-btn")
        price_text = price_div.get_text(strip=True) if price_div else ""

        if not title:
            continue

        ev: Event = {
            "title": title,
            "place": place or "Madrid",
            "time": "",  # Mosaic-ում час չկա, հետո եթե գտնենք՝ կավելացնենք
            "date": date_iso,
            "category": category_slug,
            "source_url": source_url,
            "address": "",
            "price": price_text,
            "image_url": image_url,
        }
        events.append(ev)

    return events


# ==========================
#  DB WRITE HELPERS
# ==========================

def _save_event_to_db(ev: Event) -> None:
    """
    Գրանցում է event-ը madrid_events աղյուսակում.
    date-ը պահում է ev["date"]-ով, եթե կա, ellers՝ այսօր:
    """
    try:
        from backend.events import _get_conn

        conn = _get_conn()
        cur = conn.cursor()

        date_str = ev.get("date") or _today_str()

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
                date_str,
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


# ==========================
#  DAILY REFRESH
# ==========================

def refresh_madrid_events_for_today() -> None:
    """
    Ամեն գիշեր.
    - Ջնջում է մինչև այսօրը ներառյալ նախորդ օրերի events-ները.
    - Քաշում է այսօրվա / ընթացիկ շոுனերը տարբեր կատեգորիաներից.
    """
    today = _today_str()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM madrid_events WHERE date < %s;", (today,))
        conn.commit()
        conn.close()
        logger.info("Cleared past madrid_events before refresh")
    except Exception as e:
        logger.error(f"Error clearing past events: {e}", exc_info=True)

    # 🎬 Կինո – Taquilla cartelera (մինչև 30 ֆիլմ)
    for ev in fetch_madrid_cinema_events(limit=30):
        _save_event_to_db(ev)

    # 🎭 Շոու / թատրոն / մյուզիքլ / kids / և այլն — յուրաքանչյուրից մինչև 20 event
    for category_slug, url in TAQUILLA_SHOW_CATEGORIES.items():
        shows = fetch_taquilla_show_category(url, category_slug, limit=20)
        for ev in shows:
            _save_event_to_db(ev)

    logger.info("Refreshed madrid_events for today (cinema + Taquilla shows)")


if __name__ == "__main__":
    refresh_madrid_events_for_today()
