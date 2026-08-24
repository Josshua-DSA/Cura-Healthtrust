import psycopg2
import sys
import os

# Menambahkan path config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

def check_postgres_health():
    print("=" * 60)
    print(" [HealthTrust] Checking PostgreSQL & PostGIS Extension Health")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            connect_timeout=5
        )
        cur = conn.cursor()
        
        # Check basic query
        cur.execute("SELECT version();")
        pg_version = cur.fetchone()[0]
        print(f"[OK] PostgreSQL Connected: {pg_version.split(',')[0]}")
        
        # Check PostGIS extension
        cur.execute("SELECT PostGIS_Full_Version();")
        postgis_version = cur.fetchone()[0]
        postgis_clean = postgis_version.split('"')[1] if '"' in postgis_version else postgis_version[:40]
        print(f"[OK] PostGIS Extension Active: {postgis_clean}")
        
        cur.close()
        conn.close()
        print("=" * 60)
        print(" DB Status: HEALTHY")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"[FAILED] Database connection error: {e}")
        print("=" * 60)
        print(" DB Status: DOWN (Pastikan container PostGIS sudah berjalan)")
        print("=" * 60)
        return False

if __name__ == "__main__":
    check_postgres_health()
