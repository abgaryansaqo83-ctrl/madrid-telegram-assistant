# simplified/schedule.py

import asyncio
import os
import sys
import signal
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Import from simplified module
from simplified.post_digest import post_digest, close_bot

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
INTERVAL_MINUTES = int(os.getenv("DIGEST_INTERVAL", "30"))
SCHEDULE_TYPE = os.getenv("SCHEDULE_TYPE", "interval")  # 'interval' or 'cron'
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "0 9,14,19 * * *")  # Default: 9am, 2pm, 7pm

# Initialize scheduler
scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

# Global stop event
stop_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    stop_event.set()

async def scheduled_digest():
    """Wrapper for post_digest with error handling"""
    try:
        logger.info("🔄 Running scheduled digest...")
        await post_digest()
        logger.info("✅ Scheduled digest completed")
    except Exception as e:
        logger.error(f"❌ Error in scheduled digest: {e}", exc_info=True)

async def start_scheduler():
    """
    Start the scheduler and run digest posting at configured intervals
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Madrid Bot Scheduler")
        logger.info(f"📅 Timezone: Europe/Madrid")
        logger.info(f"⏱️  Schedule Type: {SCHEDULE_TYPE}")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run initial digest immediately
        logger.info("📬 Running initial digest...")
        try:
            await post_digest()
            logger.info("✅ Initial digest posted successfully")
        except Exception as e:
            logger.error(f"❌ Error posting initial digest: {e}", exc_info=True)
        
        # Add scheduled job based on configuration
        if SCHEDULE_TYPE == "cron":
            # Cron-based scheduling (specific times)
            scheduler.add_job(
                scheduled_digest,
                CronTrigger.from_crontab(CRON_SCHEDULE, timezone="Europe/Madrid"),
                id="digest_cron",
                name="Post Digest (Cron)",
                replace_existing=True,
                misfire_grace_time=300  # 5 minutes grace period
            )
            logger.info(f"⏰ Cron schedule set: {CRON_SCHEDULE}")
        else:
            # Interval-based scheduling
            scheduler.add_job(
                scheduled_digest,
                IntervalTrigger(minutes=INTERVAL_MINUTES, timezone="Europe/Madrid"),
                id="digest_interval",
                name="Post Digest (Interval)",
                replace_existing=True,
                misfire_grace_time=300
            )
            logger.info(f"⏰ Interval schedule set: every {INTERVAL_MINUTES} minutes")
        
        # Start the scheduler
        scheduler.start()
        logger.info("✅ Scheduler started successfully")
        logger.info("=" * 60)
        
        # Print next scheduled run times
        jobs = scheduler.get_jobs()
        for job in jobs:
            next_run = job.next_run_time
            if next_run:
                logger.info(f"📌 Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Wait for stop signal
        logger.info("⏳ Scheduler is running. Press Ctrl+C to stop.")
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"💥 Critical error in scheduler: {e}", exc_info=True)
        raise
    finally:
        await shutdown()

async def shutdown():
    """Gracefully shutdown the scheduler and cleanup resources"""
    logger.info("🛑 Shutting down scheduler...")
    
    try:
        # Stop scheduler
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ Scheduler stopped")
        
        # Close bot session
        await close_bot()
        
        # Cancel any remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"🧹 Cancelling {len(tasks)} remaining tasks...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("✅ Shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

def main():
    """Main entry point"""
    try:
        # Run the async scheduler
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        logger.info("⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
