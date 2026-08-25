import pytest
import pandas as pd
import json
from pipeline.cleaner import (
    clean_and_validate_hospitals,
    normalize_kelas,
    normalize_kepemilikan,
    extract_kode_bps_from_kode_rs
)
from pipeline.storage import save_raw_snapshot, load_latest_snapshot
from pipeline.loader import generate_rs_key

def test_normalize_kelas():
    assert normalize_kelas("A") == "A"
    assert normalize_kelas("b") == "B"
    assert normalize_kelas("C ") == "C"
    assert normalize_kelas("D") == "D"
    assert normalize_kelas("Non Kelas") == "tidak_diketahui"
    assert normalize_kelas(None) == "tidak_diketahui"

def test_normalize_kepemilikan():
    assert normalize_kepemilikan("TNI AD") == "tni_polri"
    assert normalize_kepemilikan("POLRI") == "tni_polri"
    assert normalize_kepemilikan("Pemkab") == "pemerintah"
    assert normalize_kepemilikan("Kemkes ") == "pemerintah"
    assert normalize_kepemilikan("SWASTA/LAINNYA") == "swasta"
    assert normalize_kepemilikan("Perusahaan") == "swasta"
    assert normalize_kepemilikan(None) == "lainnya"

def test_extract_kode_bps():
    assert extract_kode_bps_from_kode_rs("3501016") == "3501"
    assert extract_kode_bps_from_kode_rs("3578011") == "3578"
    assert extract_kode_bps_from_kode_rs("3171011") is None
    assert extract_kode_bps_from_kode_rs("") is None

def test_generate_rs_key():
    assert generate_rs_key("RS Darsono", "3501", "3501016") == "3501016"
    key_gen = generate_rs_key("RS Baru", "3501", None)
    assert key_gen.startswith("gen_")

def test_storage_snapshot_cycle(tmp_path, monkeypatch):
    import pipeline.storage as storage_mod
    monkeypatch.setattr(storage_mod, "RAW_DATA_DIR", str(tmp_path))

    test_data = {"test_key": "test_value"}
    saved_path = save_raw_snapshot("test_source", test_data)
    assert "test_source" in saved_path

    loaded_data, path = load_latest_snapshot("test_source")
    assert loaded_data == test_data

def test_clean_and_validate_hospitals():
    raw_rs = [
        {
            "nama": "RS Sample 1",
            "alamat": "Jl. Jawa No 1",
            "telepon": "031-123456",
            "kelas": "B",
            "jenis": "RSU",
            "koordinat": [-7.25, 112.75],
            "kode": "3578001"
        },
        {
            "nama": "RS Sample Luar Jatim",
            "alamat": "Jakarta",
            "telepon": "021-9999",
            "kelas": "A",
            "jenis": "RSU",
            "koordinat": [-6.20, 106.84], # Luar Jatim
            "kode": "3578002"
        }
    ]
    raw_rekap = [
        {"kode": "3578001", "pemilik": "Pemkot"},
        {"kode": "3578002", "pemilik": "Swasta"}
    ]

    df = clean_and_validate_hospitals(raw_rs, raw_rekap)
    assert len(df) == 2
    
    # Check valid Jatim coordinates retained
    row1 = df[df["kode_rs"] == "3578001"].iloc[0]
    assert row1["lat"] == -7.25
    assert row1["lng"] == 112.75
    assert row1["kepemilikan"] == "pemerintah"
    assert row1["kelas"] == "B"

    # Check out-of-bounds coordinates nullified safely
    row2 = df[df["kode_rs"] == "3578002"].iloc[0]
    assert pd.isna(row2["lat"])
    assert pd.isna(row2["lng"])
