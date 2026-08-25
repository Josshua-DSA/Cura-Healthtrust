import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="HealthTrust Data Engineering CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Commands
    subparsers.add_parser("init-db", help="Initialize tables and PostGIS extensions")
    subparsers.add_parser("seed-wilayah", help="Seed 38 Kab/Kota Jawa Timur reference data")
    subparsers.add_parser("run-etl", help="Run full ETL pipeline")
    subparsers.add_parser("test-db", help="Run test suite for data layer")
    subparsers.add_parser("check-health", help="Check status and availability of external APIs & DB")
    
    # Scheduler parser
    sched_parser = subparsers.add_parser("scheduler", help="Run automatic ETL scheduler daemon")
    sched_parser.add_argument("--day", type=str, default="mon", help="Day of week: mon/senin, tue, wed, thu, fri, sat, sun, or daily (default: mon)")
    sched_parser.add_argument("--hour", type=int, default=7, help="Target hour in 24h format (default: 7)")
    sched_parser.add_argument("--minute", type=int, default=0, help="Target minute (default: 0)")
    sched_parser.add_argument("--timezone", type=str, default="Asia/Jakarta", help="Timezone (default: Asia/Jakarta)")
    sched_parser.add_argument("--run-now", action="store_true", help="Run ETL once immediately")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "check-health":
        from health.check_api_health import run_health_checks
        from health.check_db_health import check_postgres_health
        run_health_checks()
        print()
        check_postgres_health()
        return

    if args.command == "scheduler":
        from scheduler import run_scheduler_loop, run_etl_job
        if args.run_now:
            run_etl_job()
        run_scheduler_loop(
            target_hour=args.hour,
            target_minute=args.minute,
            day_of_week=args.day,
            timezone_str=args.timezone
        )
        return

    if args.command == "init-db":
        from pipeline.loader import init_db
        init_db()
        return

    if args.command == "seed-wilayah":
        import csv
        from pipeline.loader import get_session, upsert_ref_wilayah
        from models import EnumTipeWilayah
        session = get_session()
        csv_path = "database/seeds/ref_wilayah_jatim.csv"
        records = []
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "kode_bps": row["kode_bps"],
                    "nama_wilayah": row["nama_wilayah"],
                    "tipe": EnumTipeWilayah(row["tipe"])
                })
        upsert_ref_wilayah(session, records)
        session.close()
        return

    if args.command == "run-etl":
        from pipeline.fetcher import fetch_all_sources
        fetch_all_sources()
        return

    print(f"[HealthTrust CLI] Executing command: {args.command}")

if __name__ == "__main__":
    main()
