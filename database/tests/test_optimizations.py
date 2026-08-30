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

def test_parquet_export_existence():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    assert os.path.exists(os.path.join(exports_dir, "hospitals_clean.parquet"))
    assert os.path.exists(os.path.join(exports_dir, "bed_ratio_38_kab.parquet"))
    assert os.path.exists(os.path.join(exports_dir, "indicators_jatim.parquet"))
