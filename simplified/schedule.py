import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from post_digest import post_digest

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

async def start_scheduler():
    """
    Start scheduler to run post_digest dynamically every X minutes
    """
    # Run immediately first time
    await post_digest()

    # Schedule every 30 minutes
    scheduler.add_job(post_digest, IntervalTrigger(minutes=30))
    scheduler.start()
    print("Scheduler started: checking for new items every 30 minutes...")

    # Keep the scheduler running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(start_scheduler())
