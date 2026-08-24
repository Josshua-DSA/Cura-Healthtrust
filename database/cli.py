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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print(f"[HealthTrust CLI] Executing command: {args.command}")

if __name__ == "__main__":
    main()
