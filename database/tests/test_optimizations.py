import os
import pytest
from pipeline.geocoder import geocode_address_osm, enrich_unmapped_hospitals
from pipeline.storage import prune_old_snapshots, ensure_source_dir
from pipeline.loader import get_session
from sqlalchemy import text

def test_prune_old_snapshots_retention(tmp_path):
    # Test pruning keeping max 10
    source_dir = ensure_source_dir("test_source_prune")
    for i in range(15):
        with open(os.path.join(source_dir, f"20260830_0000{i:02d}.json"), "w") as f:
            f.write("{}")
    
    deleted = prune_old_snapshots("test_source_prune", max_keep=10)
    assert deleted >= 5
    
    remaining = [f for f in os.listdir(source_dir) if f.endswith(".json") and f != "latest.json"]
    assert len(remaining) <= 10
    
    # Cleanup
    for f in os.listdir(source_dir):
        os.remove(os.path.join(source_dir, f))
    os.rmdir(source_dir)

def test_v_choropleth_wilayah_view():
    session = get_session()
    res = session.execute(text("SELECT COUNT(*) FROM v_choropleth_wilayah;")).scalar()
    session.close()
    assert res == 38


def test_v_faskes_all_view():
    session = get_session()
    try:
        total = session.execute(text("SELECT COUNT(*) FROM v_faskes_all;")).scalar()
        rs_count = session.execute(text("SELECT COUNT(*) FROM v_faskes_all WHERE jenis_faskes = 'rumah_sakit';")).scalar()
        pkm_count = session.execute(text("SELECT COUNT(*) FROM v_faskes_all WHERE jenis_faskes = 'puskesmas';")).scalar()
        assert total >= 1400
        assert rs_count == 447
        assert pkm_count >= 900
    finally:
        session.close()


def test_pg_trgm_and_unaccent_fuzzy_search():
    session = get_session()
    try:
        # Test pg_trgm fuzzy matching
        res = session.execute(
            text("SELECT nama_rs FROM tbl_rumah_sakit WHERE similarity(nama_rs, 'RS Dr Sutomo') > 0.25 LIMIT 1;")
        ).fetchone()
        assert res is not None
        assert "Soetomo" in res[0] or "dr." in res[0].lower()

        # Test unaccent function
        unaccent_test = session.execute(text("SELECT unaccent('Hôpital Sehat');")).scalar()
        assert unaccent_test == "Hopital Sehat"
    finally:
        session.close()


def test_parquet_export_existence():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    assert os.path.exists(os.path.join(exports_dir, "hospitals_clean.parquet"))
    assert os.path.exists(os.path.join(exports_dir, "bed_ratio_38_kab.parquet"))
    assert os.path.exists(os.path.join(exports_dir, "indicators_jatim.parquet"))

def test_data_freshness_and_projection_2026():
    import pandas as pd
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    df_rs = pd.read_parquet(os.path.join(exports_dir, "hospitals_clean.parquet"))
    assert "coverage_periode" in df_rs.columns
    assert (df_rs["coverage_periode"] == "2026-LIVE").all()

    df_ratio = pd.read_parquet(os.path.join(exports_dir, "bed_ratio_38_kab.parquet"))
    assert "proyeksi_penduduk_2026" in df_ratio.columns
    assert "rasio_tt_proyeksi_2026" in df_ratio.columns
    assert "kategori_who_proyeksi_2026" in df_ratio.columns
    assert (df_ratio["coverage_periode"] == "2026-PROJECTED").all()
    # Verify projection is higher than 2021 population
    assert (df_ratio["proyeksi_penduduk_2026"] > df_ratio["jumlah_penduduk_2021"]).all()


def test_reference_tables_seed():
    from models import RefSumberData, RefIcd10

    session = get_session()
    try:
        sources = session.query(RefSumberData).all()
        assert len(sources) >= 6
        source_ids = {s.source_id for s in sources}
        assert "sirs_kemenkes" in source_ids
        assert "opendata_jatim" in source_ids

        icds = session.query(RefIcd10).all()
        assert len(icds) >= 20
        icd_kodes = {i.kode for i in icds}
        assert "A15" in icd_kodes  # TB Paru
        assert "A90" in icd_kodes  # DBD
        assert "E45" in icd_kodes  # Stunting
    finally:
        session.close()

