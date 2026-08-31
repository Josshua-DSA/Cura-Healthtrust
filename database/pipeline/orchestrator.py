import os
import logging
import json
from datetime import datetime
from typing import Dict, Any
import pandas as pd

from pipeline.storage import load_latest_snapshot
from etl.transform.clean_hospitals import clean_and_validate_hospitals
from etl.transform.clean_puskesmas import clean_and_validate_puskesmas
from etl.transform.clean_spatial import clean_and_validate_districts
from etl.load.load_to_postgis import load_all_to_postgis
from pipeline.opendata_crawler import crawl_and_parse_opendata_csv
from pipeline.geocoder import enrich_unmapped_hospitals
from pipeline.loader import get_session
from pipeline.audit import start_pipeline_log, finish_pipeline_log
from models import EnumPipelineStatus

logger = logging.getLogger("ETLOrchestrator")

def execute_full_etl() -> Dict[str, Any]:
    """
    Complete End-to-End ETL Pipeline (Action Plan v2.0):
    1. Read Raw Snapshot (or fetch live)
    2. Clean & Validate Hospital data with Quality Gates
    3. Generate 3 Export Datasets: hospitals_clean.csv, bed_ratio_38_kab.csv, indicators_jatim.csv
    4. Clean & Validate District Polygons & Ratio
    5. Ingest Thematic Health Indicators from OpenData Jatim
    6. Idempotent Upsert to PostgreSQL/PostGIS
    7. Pre-compute Aggregate Dashboard Stats
    8. Write Audit Log
    """
    logger.info("=" * 60)
    logger.info(" [HealthTrust] Starting Complete ETL Execution & Loading (v2.0)")
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
        logger.info("Step 2: Cleaning & Validating hospital records with Quality Gates...")
        df_rs = clean_and_validate_hospitals(raw_rs_items, raw_rekap_items)
        rs_records = df_rs.to_dict(orient="records")

        # Step 2B: Optional OSM Geocoding enrichment for unmapped hospitals
        try:
            rs_records = enrich_unmapped_hospitals(rs_records, max_lookups=5)
            df_rs = pd.DataFrame(rs_records)
        except Exception as e:
            logger.warning(f"[Geocoder] Geocoding enrichment skipped/failed: {e}")
        
        # Save clean export datasets (CSV + Parquet format)
        exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        export_rs_path = os.path.join(exports_dir, "hospitals_clean.csv")
        export_rs_parquet = os.path.join(exports_dir, "hospitals_clean.parquet")
        df_rs.to_csv(export_rs_path, index=False)
        try:
            df_rs.to_parquet(export_rs_parquet, index=False)
            logger.info(f"[Export] Saved clean hospital exports -> {export_rs_path} & {export_rs_parquet}")
        except Exception as e:
            logger.info(f"[Export] Saved clean hospital export -> {export_rs_path} (parquet skipped: {e})")

        # Step 3: Spatial Districts & Ratio Export CSV 2: bed_ratio_38_kab.csv
        logger.info("Step 3: Cleaning district polygons and precomputing WHO ratio export...")
        wilayah_records, df_ratio = clean_and_validate_districts(geojson_raw, rasio_tt_raw)
        
        export_ratio_path = os.path.join(exports_dir, "bed_ratio_38_kab.csv")
        export_ratio_parquet = os.path.join(exports_dir, "bed_ratio_38_kab.parquet")
        df_ratio.to_csv(export_ratio_path, index=False)
        try:
            df_ratio.to_parquet(export_ratio_parquet, index=False)
        except Exception:
            pass
        logger.info(f"[Export] Saved district ratio export -> {export_ratio_path}")

        # Step 4: Indicators Thematic Export CSV 3: indicators_jatim.csv
        logger.info("Step 4: Ingesting thematic indicators from Open Data Jatim...")
        indikator_records = crawl_and_parse_opendata_csv()
        if indikator_records:
            df_ind = pd.DataFrame(indikator_records)
            export_ind_path = os.path.join(exports_dir, "indicators_jatim.csv")
            export_ind_parquet = os.path.join(exports_dir, "indicators_jatim.parquet")
            df_ind.to_csv(export_ind_path, index=False)
            try:
                df_ind.to_parquet(export_ind_parquet, index=False)
            except Exception:
                pass
            logger.info(f"[Export] Saved thematic health indicators export -> {export_ind_path}")

        # Step 4B: Clean & Export Puskesmas Dataset
        logger.info("Step 4B: Cleaning & Exporting Puskesmas dataset (Domain A - PRD F02)...")
        pkm_seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seeds", "ref_puskesmas_jatim.csv")
        puskesmas_records = []
        if os.path.exists(pkm_seed_path):
            df_pkm_raw = pd.read_csv(pkm_seed_path)
            df_pkm = clean_and_validate_puskesmas(df_pkm_raw.to_dict(orient="records"))
            puskesmas_records = df_pkm.to_dict(orient="records")
            export_pkm_path = os.path.join(exports_dir, "puskesmas_clean.csv")
            export_pkm_parquet = os.path.join(exports_dir, "puskesmas_clean.parquet")
            df_pkm.to_csv(export_pkm_path, index=False)
            try:
                df_pkm.to_parquet(export_pkm_parquet, index=False)
                logger.info(f"[Export] Saved clean puskesmas exports -> {export_pkm_path} & {export_pkm_parquet}")
            except Exception as e:
                logger.info(f"[Export] Saved clean puskesmas export -> {export_pkm_path} (parquet skipped: {e})")

        # Step 5: Load to PostgreSQL/PostGIS
        logger.info("Step 5: Loading all processed datasets to PostgreSQL/PostGIS...")
        penduduk_records = []
        for r in df_ratio.to_dict(orient="records"):
            penduduk_records.append({
                "kode_bps": r["kode_bps"],
                "tahun": 2024,
                "jumlah_penduduk": r.get("jumlah_penduduk_2021", r.get("jumlah_penduduk", 0)),
                "sumber": "SIRS Kemenkes / Disdukcapil"
            })

        rasio_items = rasio_tt_raw.get("wilayah", []) if rasio_tt_raw else []

        load_summary = load_all_to_postgis(
            rs_records=rs_records,
            wilayah_records=wilayah_records,
            penduduk_records=penduduk_records,
            indikator_records=indikator_records,
            rasio_raw_list=rasio_items,
            puskesmas_records=puskesmas_records
        )
        total_loaded = sum(load_summary.values())

        # Step 6: Audit Log Success
        finish_pipeline_log(
            session=session,
            log_id=audit_entry.id,
            status=EnumPipelineStatus.SUCCESS,
            record_extracted=total_extracted,
            record_loaded=total_loaded
        )

        logger.info("=" * 60)
        logger.info(f" [SUCCESS] Complete ETL v2.0 Finished. Extracted: {total_extracted} | Loaded: {total_loaded}")
        logger.info("=" * 60)

        return {
            "status": "SUCCESS",
            "extracted": total_extracted,
            "loaded": total_loaded,
            "exports": [export_rs_path, export_ratio_path, os.path.join(exports_dir, "indicators_jatim.csv")]
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
