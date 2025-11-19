import asyncio
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .post_digest import post_digest  # package-relative import

logging.basicConfig(level=logging.INFO)

INTERVAL_MINUTES = int(os.getenv("DIGEST_INTERVAL", 30))

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

async def start_scheduler():
    """
    Start scheduler to run post_digest dynamically every INTERVAL_MINUTES
    """
    # Run immediately first time
    await post_digest()

    # Schedule recurring
    scheduler.add_job(post_digest, IntervalTrigger(minutes=INTERVAL_MINUTES))
    scheduler.start()
    logging.info(f"Scheduler started: checking for new items every {INTERVAL_MINUTES} minutes...")

    # Keep scheduler running
    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(start_scheduler())
