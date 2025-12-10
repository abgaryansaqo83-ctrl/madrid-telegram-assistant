# backend/jobs.py

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple

import psycopg  # պետք է ավելացնես requirements.txt-ում

logger = logging.getLogger(__name__)

# Կօգտագործենք նույն DSN-ը, ինչ باقی backend-ը
JOBS_DB_URL = os.getenv("EVENTS_DB_URL") or os.getenv("DATABASE_URL")

# Տիպեր
Job = Dict[str, str]
Match = Tuple[Job, Job]


def _get_conn():
    """
    Բացում է նոր PostgreSQL connection `JOBS_DB_URL`-ով.
    """
    if not JOBS_DB_URL:
        raise RuntimeError("JOBS_DB_URL/DATABASE_URL is not set in environment")
    return psycopg.connect(JOBS_DB_URL)


# ======================== Schema init helpers ==========================

def init_jobs_schema() -> None:
    """
    Ստեղծում է madrid_jobs և madrid_posted աղյուսակները, եթե դեռ չկան.
    Կանչիր բոտի start-ի ժամանակ (օրինակ bot.py main-ում մեկ անգամ).
    """
    sql = """
    CREATE TABLE IF NOT EXISTS madrid_jobs (
        id         SERIAL PRIMARY KEY,
        user_id    BIGINT NOT NULL,
        username   TEXT,
        role       VARCHAR(16) NOT NULL,  -- 'offer' կամ 'request'
        text       TEXT NOT NULL,
        city       TEXT NOT NULL DEFAULT 'madrid',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_madrid_jobs_role_created
        ON madrid_jobs (role, created_at);

    CREATE TABLE IF NOT EXISTS madrid_posted (
        id         SERIAL PRIMARY KEY,
        key        TEXT UNIQUE NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
        logger.info("madrid_jobs and madrid_posted tables ensured/initialized")
    except Exception as e:
        logger.error(f"Error initializing jobs schema: {e}", exc_info=True)
        raise


# ======================== Core DB helpers ==============================

def _insert_job(user, text: str, role: str) -> None:
    """
    Ներքին helper՝ INSERT madrid_jobs.
    user – aiogram-ի User օրինակը կամ object, որ ունի id և username.
    """
    sql = """
    INSERT INTO madrid_jobs (user_id, username, role, text)
    VALUES (%(user_id)s, %(username)s, %(role)s, %(text)s);
    """
    params = {
        "user_id": int(getattr(user, "id", 0)),
        "username": getattr(user, "username", None),
        "role": role,
        "text": text,
    }
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
        logger.info("Inserted job (%s) from user_id=%s", role, params["user_id"])
    except Exception as e:
        logger.error(f"Error inserting job ({role}): {e}", exc_info=True)
        raise


def _fetch_jobs(role: str, days: int = 30) -> List[Job]:
    """
    Վերցնում է վերջին `days` օրերի jobs-երը տվյալ role-ի համար.
    """
    since = datetime.utcnow() - timedelta(days=days)
    sql = """
    SELECT id, user_id, username, role, text, city, created_at
    FROM madrid_jobs
    WHERE role = %(role)s
      AND created_at >= %(since)s
    ORDER BY created_at DESC;
    """
    params = {"role": role, "since": since}
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching jobs for role={role}: {e}", exc_info=True)
        return []

    jobs: List[Job] = []
    for job_id, user_id, username, role, text, city, created_at in rows:
        jobs.append(
            {
                "id": job_id,
                "user_id": user_id,
                "username": username,
                "role": role,
                "text": text,
                "city": city,
                "created_at": created_at.isoformat(),
            }
        )
    return jobs


# ======================== Public API (offers/requests) =================

def add_offer(user, text: str) -> None:
    """
    Add job offer – հիմա INSERT է անում madrid_jobs աղյուսակում.
    """
    _insert_job(user, text, role="offer")


def add_request(user, text: str) -> None:
    """
    Add job request – INSERT madrid_jobs-ում role='request'.
    """
    _insert_job(user, text, role="request")


def find_matches(days: int = 30) -> List[Match]:
    """
    Find matches between requests and offers վերջին `days` օրերից.
    Keyword matching logic-ը պահում ենք նույնը, բայց արդեն DB row-երով.
    """
    try:
        requests = _fetch_jobs(role="request", days=days)
        offers = _fetch_jobs(role="offer", days=days)

        matches: List[Match] = []

        for req in requests:
            for off in offers:
                req_words = set(req["text"].lower().split())
                off_words = set(off["text"].lower().split())
                common_words = req_words & off_words

                if len(common_words) >= 2 or (
                    len(common_words) >= 1 and len(req_words) <= 3
                ):
                    matches.append((req, off))

        logger.info("Found %d matches", len(matches))
        return matches
    except Exception as e:
        logger.error(f"Error finding matches: {e}", exc_info=True)
        return []


# ======================== Posted items (anti-duplicate)
