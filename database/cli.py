import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="HealthTrust Data Engineering CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Commands
    subparsers.add_parser("init-db", help="Initialize tables and PostGIS extensions")
    subparsers.add_parser("seed-wilayah", help="Seed 38 Kab/Kota Jawa Timur reference data")
    subparsers.add_parser("seed-references", help="Seed ref_sumber_data and ref_icd10 tables")
    subparsers.add_parser("seed-puskesmas", help="Seed 960+ Puskesmas records across 38 Kab/Kota")
    subparsers.add_parser("seed-workforce", help="Seed healthcare workforce records (Doctor, Nurse, Midwife)")
    subparsers.add_parser("seed-morbidity", help="Seed patient disease morbidity records across 38 Kab/Kota")
    subparsers.add_parser("seed-kia", help="Seed Maternal and Child Health (KIA) records")
    subparsers.add_parser("seed-surveillance", help="Seed Weekly Disease Surveillance records")
    subparsers.add_parser("seed-alert-rules", help="Seed default early warning alert rules")
    subparsers.add_parser("evaluate-alerts", help="Evaluate alert rules against current data and generate events")
    subparsers.add_parser("build-ml-features", help="Build unified ML readiness dataset feature store")
    subparsers.add_parser("run-etl", help="Run full ETL pipeline")
    subparsers.add_parser("test-db", help="Run test suite for data layer")
    subparsers.add_parser("check-health", help="Check status and availability of external APIs & DB")
    
    # Geocode parser
    geocode_parser = subparsers.add_parser("geocode-pending", help="Batch geocode hospitals with NULL coordinates via OSM Nominatim")
    geocode_parser.add_argument("--max", type=int, default=50, help="Max hospitals to geocode per run (default: 50, Nominatim rate: 1 req/sec)")
    
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

    if args.command == "seed-references":
        import csv
        import os
        from pipeline.loader import get_session, upsert_ref_sumber_data, upsert_ref_icd10
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 1. Seed ref_sumber_data
        src_path = os.path.join(base_dir, "seeds", "ref_sumber_data.csv")
        if os.path.exists(src_path):
            with open(src_path, mode="r", encoding="utf-8") as f:
                records = list(csv.DictReader(f))
                upsert_ref_sumber_data(session, records)

        # 2. Seed ref_icd10
        icd_path = os.path.join(base_dir, "seeds", "ref_icd10.csv")
        if os.path.exists(icd_path):
            with open(icd_path, mode="r", encoding="utf-8") as f:
                records = list(csv.DictReader(f))
                upsert_ref_icd10(session, records)

        session.close()
        return

    if args.command == "seed-puskesmas":
        import csv
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_puskesmas
        from etl.transform.clean_puskesmas import clean_and_validate_puskesmas
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pkm_path = os.path.join(base_dir, "seeds", "ref_puskesmas_jatim.csv")
        if os.path.exists(pkm_path):
            df_raw = pd.read_csv(pkm_path)
            df_clean = clean_and_validate_puskesmas(df_raw.to_dict(orient="records"))
            upsert_puskesmas(session, df_clean.to_dict(orient="records"))
        session.close()
        return

    if args.command == "seed-workforce":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_tenaga_kesehatan
        from etl.transform.clean_workforce import clean_and_validate_workforce
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "seeds", "ref_nakes_jatim.csv")
        if os.path.exists(path):
            df_raw = pd.read_csv(path)
            df_clean = clean_and_validate_workforce(df_raw.to_dict(orient="records"))
            upsert_tenaga_kesehatan(session, df_clean.to_dict(orient="records"))
        session.close()
        return

    if args.command == "seed-morbidity":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_pasien_morbiditas
        from etl.transform.clean_morbidity import clean_and_validate_morbidity
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "seeds", "ref_morbiditas_jatim.csv")
        if os.path.exists(path):
            df_raw = pd.read_csv(path)
            df_clean = clean_and_validate_morbidity(df_raw.to_dict(orient="records"))
            upsert_pasien_morbiditas(session, df_clean.to_dict(orient="records"))
        session.close()
        return

    if args.command == "seed-kia":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_indikator_kia
        from etl.transform.clean_kia import clean_and_validate_kia
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "seeds", "ref_kia_jatim.csv")
        if os.path.exists(path):
            df_raw = pd.read_csv(path)
            df_clean = clean_and_validate_kia(df_raw.to_dict(orient="records"))
            upsert_indikator_kia(session, df_clean.to_dict(orient="records"))
        session.close()
        return

    if args.command == "seed-surveillance":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_penyakit_surveillance
        from etl.transform.clean_surveillance import clean_and_validate_surveillance
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "seeds", "ref_surveillance_jatim.csv")
        if os.path.exists(path):
            df_raw = pd.read_csv(path)
            df_clean = clean_and_validate_surveillance(df_raw.to_dict(orient="records"))
            upsert_penyakit_surveillance(session, df_clean.to_dict(orient="records"))
        session.close()
        return

    if args.command == "seed-alert-rules":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_alert_rules
        session = get_session()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "seeds", "ref_alert_rules.csv")
        if os.path.exists(path):
            df_raw = pd.read_csv(path)
            upsert_alert_rules(session, df_raw.to_dict(orient="records"))
        session.close()
        return

    if args.command == "evaluate-alerts":
        import os
        import pandas as pd
        from pipeline.loader import get_session, upsert_alert_events
        from etl.transform.evaluate_alerts import evaluate_active_alerts
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exports_dir = os.path.join(base_dir, "exports")
        df_alerts = evaluate_active_alerts(exports_dir)
        session = get_session()
        upsert_alert_events(session, df_alerts.to_dict(orient="records"))
        session.close()
        return

    if args.command == "build-ml-features":
        import os
        from etl.transform.build_ml_features import build_ml_readiness_dataset
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exports_dir = os.path.join(base_dir, "exports")
        build_ml_readiness_dataset(exports_dir)
        return

    if args.command == "test-db":
        import pytest
        sys.exit(pytest.main(["database/tests/", "-v"]))

    if args.command == "run-etl":
        from pipeline.fetcher import fetch_all_sources
        from pipeline.orchestrator import execute_full_etl
        fetch_all_sources()
        execute_full_etl()
        return

    if args.command == "geocode-pending":
        from pipeline.geocoder import geocode_pending_from_db
        result = geocode_pending_from_db(max_lookups=args.max)
        print(f"[Geocoder] Done. Resolved: {result['resolved']}, Still pending: {result['remaining']}.")
        return

    print(f"[HealthTrust CLI] Executing command: {args.command}")

if __name__ == "__main__":
    main()
