import os
import sys
import time
import argparse
import logging
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HealthTrustScheduler")

WEEKDAYS = {
    "mon": 0, "monday": 0, "senin": 0,
    "tue": 1, "tuesday": 1, "selasa": 1,
    "wed": 2, "wednesday": 2, "rabu": 2,
    "thu": 3, "thursday": 3, "kamis": 3,
    "fri": 4, "friday": 4, "jumat": 4,
    "sat": 5, "saturday": 5, "sabtu": 5,
    "sun": 6, "sunday": 6, "minggu": 6
}
WEEKDAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

def run_etl_job():
    """Trigger the ETL workflow."""
    logger.info("=" * 50)
    logger.info("[Scheduler] Starting Scheduled ETL Pipeline Job")
    logger.info("=" * 50)
    try:
        from pipeline.fetcher import fetch_all_sources
        from pipeline.orchestrator import execute_full_etl
        fetch_all_sources()
        result = execute_full_etl()
        logger.info(f"[Scheduler] ETL executed successfully: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] ETL Job failed with error: {e}")

def run_scheduler_loop(
    target_hour: int = 7,
    target_minute: int = 0,
    day_of_week: Optional[str] = "mon",
    timezone_str: str = "Asia/Jakarta"
):
    """
    Lightweight scheduler loop.
    - day_of_week: 'mon'..'sun' or None (runs every day if None or 'daily').
    - target_hour: 0..23
    - target_minute: 0..59
    """
    tz = ZoneInfo(timezone_str)
    
    target_weekday = None
    if day_of_week and day_of_week.lower() not in ("daily", "all", "everyday", "*", "none"):
        normalized = day_of_week.strip().lower()
        if normalized in WEEKDAYS:
            target_weekday = WEEKDAYS[normalized]
        else:
            logger.warning(f"Unknown day_of_week '{day_of_week}', defaulting to every day.")

    schedule_desc = (
        f"Every {WEEKDAY_NAMES[target_weekday]} at {target_hour:02d}:{target_minute:02d} ({timezone_str})"
        if target_weekday is not None
        else f"Every day at {target_hour:02d}:{target_minute:02d} ({timezone_str})"
    )
    logger.info(f"[Scheduler] Initialized. Schedule: {schedule_desc}")

    last_run_date = None

    while True:
        now = datetime.now(tz)
        current_date = now.date()

        day_matches = (target_weekday is None) or (now.weekday() == target_weekday)
        time_matches = (now.hour == target_hour and now.minute == target_minute)

        if day_matches and time_matches and last_run_date != current_date:
            logger.info(f"[Scheduler] Trigger match at {now.strftime('%Y-%m-%d %H:%M:%S %Z (%A)')}")
            run_etl_job()
            last_run_date = current_date
            time.sleep(60)
        else:
            time.sleep(15)

def main():
    parser = argparse.ArgumentParser(description="HealthTrust Database & ETL Scheduler Daemon")
    parser.add_argument("--day", type=str, default="mon", help="Day of week: mon/senin, tue, wed, thu, fri, sat, sun, or daily (default: mon)")
    parser.add_argument("--hour", type=int, default=7, help="Target hour in 24h format (default: 7)")
    parser.add_argument("--minute", type=int, default=0, help="Target minute (default: 0)")
    parser.add_argument("--timezone", type=str, default="Asia/Jakarta", help="Timezone (default: Asia/Jakarta)")
    parser.add_argument("--run-now", action="store_true", help="Execute job immediately once before starting loop")

    args = parser.parse_args()

    if args.run_now:
        run_etl_job()

    run_scheduler_loop(
        target_hour=args.hour,
        target_minute=args.minute,
        day_of_week=args.day,
        timezone_str=args.timezone
    )

if __name__ == "__main__":
    main()
