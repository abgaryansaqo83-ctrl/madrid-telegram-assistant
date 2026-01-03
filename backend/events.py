# backend/events.py

import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

import psycopg  # ensure psycopg is in requirements.txt

logger = logging.getLogger(__name__)

# ENV variable with DSN of the DB (կարող է լինել նույն DATABASE_URL-ը)
EVENTS_DB_URL = os.getenv("EVENTS_DB_URL") or os.getenv("DATABASE_URL")

Event = Dict[str, str]


def _get_conn():
    """
    Բացում է նոր PostgreSQL connection.
    EVENTS_DB_URL օրինակ:
      postgres://user:password@host:port/dbname
    """
    if not EVENTS_DB_URL:
        raise RuntimeError("EVENTS_DB_URL is not set (or DATABASE_URL missing)")
    return psycopg.connect(EVENTS_DB_URL)


def init_events_schema() -> None:
    """
    Ստեղծում է madrid_events աղյուսակը, եթե դեռ չկա.
    Համապատասխանում է refresh_madrid_events_for_today()-ի INSERT-ին.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS madrid_events (
        id          SERIAL PRIMARY KEY,
        title       TEXT NOT NULL,
        place       TEXT,
        start_time  TIMESTAMPTZ,
        date        DATE NOT NULL,
        category    VARCHAR(32) NOT NULL,   -- cinema, theatre, restaurant, holiday
        source_url  TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_madrid_events_category_date
        ON madrid_events (category, date);

    CREATE INDEX IF NOT EXISTS idx_madrid_events_category_start
        ON madrid_events (category, start_time);

    CREATE UNIQUE INDEX IF NOT EXISTS uniq_madrid_events_identity
        ON madrid_events (category, title, place, date);
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
        logger.info("madrid_events table ensured/initialized")
    except Exception as e:
        logger.error(f"Error initializing madrid_events schema: {e}", exc_info=True)
        raise


def upsert_event(
    category: str,
    title: str,
    place: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    city: str = "Madrid",
    link: Optional[str] = None,
    extra: Optional[Dict] = None,
) -> None:
    """
    Հնարավոր է վաղը պետք գա ավելի ճշգրիտ upsert.
    Հիմա պահում ենք backward compatible, բայց refresh_madrid_events_for_today()
    արդեն իր SQL INSERT-ով է աշխատում.
    """
    event_date = start_time.date()
    sql = """
    INSERT INTO madrid_events
        (category, title, place, start_time, date, source_url, updated_at)
    VALUES
        (%(category)s, %(title)s, %(place)s, %(start_time)s, %(date)s,
         %(source_url)s, now())
    ON CONFLICT (category, title, place, date)
    DO UPDATE SET
        start_time = EXCLUDED.start_time,
        source_url = EXCLUDED.source_url,
        updated_at = now();
    """

    params = {
        "category": category,
        "title": title,
        "place": place,
        "start_time": start_time,
        "date": event_date,
        "source_url": link,
    }

    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
        logger.debug("Madrid event upserted: %s — %s", category, title)
    except Exception as e:
        logger.error(f"Error upserting Madrid event '{title}': {e}", exc_info=True)
        raise


def _fetch_upcoming_events(category: str, limit: int = 3) -> List[Event]:
    """
    Վերցնում է random events-ներ տրված category-ի համար.
    Փոփոխված logic:
      - Նախ փորձում ենք գտնել event-ներ այսօրից սկսած առաջիկա 30 օրերի համար.
      - Եթե չկան, fallback ենք անում վերջին 30 օրերի event-ների վրա.
    """
    today = date.today()
    plus_30 = today + timedelta(days=30)
    minus_30 = today - timedelta(days=30)

    try:
        with _get_conn() as conn, conn.cursor() as cur:
            # 1) Առաջիկա 30 օրերի event-ներ
            sql_upcoming = """
            SELECT title, place, start_time, source_url
            FROM madrid_events
            WHERE category = %(category)s
              AND date BETWEEN %(today)s AND %(plus_30)s
            ORDER BY RANDOM()
            LIMIT %(limit)s;
            """
            params_upcoming = {
                "category": category,
                "today": today,
                "plus_30": plus_30,
                "limit": limit,
            }
            cur.execute(sql_upcoming, params_upcoming)
            rows = cur.fetchall()

            # 2) Եթե չկան, fallback վերջին 30 օրերին
            if not rows:
                sql_past = """
                SELECT title, place, start_time, source_url
                FROM madrid_events
                WHERE category = %(category)s
                  AND date BETWEEN %(minus_30)s AND %(today)s
                ORDER BY RANDOM()
                LIMIT %(limit)s;
                """
                params_past = {
                    "category": category,
                    "minus_30": minus_30,
                    "today": today,
                    "limit": limit,
                }
                cur.execute(sql_past, params_past)
                rows = cur.fetchall()

    except Exception as e:
        logger.error(
            f"Error fetching madrid_events for category='{category}': {e}",
            exc_info=True,
        )
        return []

    events: List[Event] = []
    for title, place, start_time, source_url in rows:
        if isinstance(start_time, datetime):
            time_str = start_time.strftime("%d.%m %H:%M")
        elif start_time:
            time_str = str(start_time)
        else:
            time_str = ""

        events.append(
            {
                "title": title or "",
                "place": place or "",
                "time": time_str,
                "url": source_url or "",
            }
        )
    return events

def get_upcoming_cinema_events(limit: int = 2) -> List[Event]:
    """
    Առաջիկա 🎬 cinema event-ներ Մադրիդում.
    """
    return _fetch_upcoming_events("cinema", limit=limit)


def get_upcoming_theatre_events(limit: int = 2) -> List[Event]:
    """
    Առաջիկա 🎭 թատրոնի event-ներ Մադրիդում.
    """
    return _fetch_upcoming_events("theatre", limit=limit)


def get_upcoming_restaurant_events(limit: int = 2) -> List[Event]:
    """
    Առաջիկա 🍽 ռեստորանային / բարային event-ներ.
    """
    return _fetch_upcoming_events("restaurant", limit=limit)


def get_upcoming_holiday_events(limit: int = 2) -> List[Event]:
    """
    Առաջիկա 🎉 քաղաքային տոնական event-ներ (Christmas, ՆԳ, փառատոններ...).
    """
    return _fetch_upcoming_events("holiday", limit=limit)
