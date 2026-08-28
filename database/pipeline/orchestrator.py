import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

from pipeline.storage import load_latest_snapshot
from pipeline.cleaner import clean_and_validate_hospitals
from pipeline.opendata_crawler import crawl_and_parse_opendata_csv
from pipeline.loader import (
    get_session, init_db, upsert_ref_wilayah, upsert_rumah_sakit,
    upsert_penduduk, recompute_agregat_wilayah, upsert_indikator_kesehatan
)
from pipeline.audit import start_pipeline_log, finish_pipeline_log
from models import EnumPipelineStatus

logger = logging.getLogger("ETLOrchestrator")

def execute_full_etl() -> Dict[str, Any]:
    """
    Complete End-to-End ETL Pipeline:
    1. Read Raw Snapshot (or fetch live)
    2. Clean & Validate Hospital data (Pandera)
    3. Idempotent Upsert to PostgreSQL/PostGIS (tbl_rumah_sakit, ref_wilayah, tbl_penduduk)
    4. Pre-compute Aggregate Dashboard Stats (tbl_agregat_wilayah)
    5. Audit trail log (tbl_pipeline_log)
    """
    logger.info("=" * 60)
    logger.info(" [HealthTrust] Starting Complete ETL Execution & Loading")
    logger.info("=" * 60)

    session = get_session()
    audit_entry = start_pipeline_log(session, "full_etl_sirs_kemenkes")
    
    total_extracted = 0
    total_loaded = 0

    try:
        # Step 1: Load Snapshots
        rs_list_raw, _ = load_latest_snapshot("sirs_kemenkes_list")
        rekap_rs_raw, _ = load_latest_snapshot("sirs_kemenkes_rekap")
        rasio_tt_raw, _ = load_latest_snapshot("sirs_kemenkes_rasio_tt")
        geojson_raw, _ = load_latest_snapshot("sirs_kemenkes_geojson")

        raw_rs_items = rs_list_raw.get("rs", []) if rs_list_raw else []
        raw_rekap_items = rekap_rs_raw.get("data", []) if rekap_rs_raw else []
        total_extracted = len(raw_rs_items)

        # Step 2: Clean & Validate RS
        logger.info("Step 2: Cleaning & Validating hospital records with Action Plan Quality Rules...")
        df_rs = clean_and_validate_hospitals(raw_rs_items, raw_rekap_items)
        
        # Save clean export CSV for data analysts
        export_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports", "hospitals_clean.csv")
        df_rs.to_csv(export_csv_path, index=False)
        logger.info(f"[Export] Saved clean hospital export to {export_csv_path}")

        rs_records = df_rs.to_dict(orient="records")

        # Step 3: Seed/Update GeoJSON polygon into ref_wilayah if available
        if geojson_raw and "features" in geojson_raw:
            logger.info("Step 3A: Updating GeoJSON boundaries in ref_wilayah...")
            wilayah_records = []
            penduduk_records = []
            for feat in geojson_raw.get("features", []):
                props = feat.get("properties", {})
                kbps = str(props.get("KODE_BPS") or props.get("ID2013", "")).strip()
                nama = props.get("PROVINSI", "")
                pddk = int(props.get("jumlah_penduduk", 0))
                geom_json = json.dumps(feat.get("geometry", {}))
                
                if kbps:
                    tipe = "KOTA" if "kota" in nama.lower() else "KABUPATEN"
                    wilayah_records.append({
                        "kode_bps": kbps,
                        "nama_wilayah": f"Kabupaten {nama}" if tipe == "KABUPATEN" and not nama.lower().startswith("kab") else (f"Kota {nama}" if tipe == "KOTA" and not nama.lower().startswith("kota") else nama),
                        "tipe": tipe,
                        "geojson_geom": geom_json
                    })
                    if pddk > 0:
                        penduduk_records.append({
                            "kode_bps": kbps,
                            "tahun": 2024,
                            "jumlah_penduduk": pddk,
                            "sumber": "SIRS Kemenkes GeoJSON"
                        })
            if wilayah_records:
                upsert_ref_wilayah(session, wilayah_records)
            if penduduk_records:
                upsert_penduduk(session, penduduk_records)

        # Step 3B: Upsert Hospitals
        logger.info("Step 3B: Upserting hospitals into tbl_rumah_sakit...")
        loaded_rs = upsert_rumah_sakit(session, rs_records)
        total_loaded += loaded_rs

        # Step 3C: Ingest Thematic Health Indicators from OpenData Jatim CSV
        logger.info("Step 3C: Ingesting thematic indicators from Open Data Jatim...")
        indikator_records = crawl_and_parse_opendata_csv()
        if indikator_records:
            loaded_ind = upsert_indikator_kesehatan(session, indikator_records)
            total_loaded += loaded_ind

        # Step 4: Pre-compute Aggregates
        logger.info("Step 4: Pre-computing aggregates in tbl_agregat_wilayah...")
        rasio_items = rasio_tt_raw.get("wilayah", []) if rasio_tt_raw else []
        recompute_agregat_wilayah(session, tahun=2024, rasio_data_list=rasio_items)

        # Step 5: Audit Log Success
        finish_pipeline_log(
            session=session,
            log_id=audit_entry.id,
            status=EnumPipelineStatus.SUCCESS,
            record_extracted=total_extracted,
            record_loaded=total_loaded
        )

        logger.info("=" * 60)
        logger.info(f" [SUCCESS] Complete ETL Finished. Extracted: {total_extracted} | Loaded: {total_loaded}")
        logger.info("=" * 60)

        return {
            "status": "SUCCESS",
            "extracted": total_extracted,
            "loaded": total_loaded
        }

    except Exception as e:
        logger.error(f"[ERROR] ETL Pipeline failed: {e}")
        session.rollback()
        finish_pipeline_log(
            session=session,
            log_id=audit_entry.id,
            status=EnumPipelineStatus.FAILED,
            record_extracted=total_extracted,
            record_loaded=total_loaded,
            error_message=str(e)
        )
        raise e
    finally:
        session.close()
