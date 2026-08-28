import pytest
import math
import pandas as pd
from pipeline.cleaner import (
    sanitize_coordinates,
    normalize_text_clean,
    normalize_telepon,
    normalize_nama_rs,
    normalize_kepemilikan,
    clean_and_validate_hospitals,
    JATIM_LAT_MIN, JATIM_LAT_MAX, JATIM_LNG_MIN, JATIM_LNG_MAX
)

# ===== Coordinate Sanitization Tests =====

def test_sanitize_coordinates_dummy():
    """Rule: Dummy Kemenkes [-2.4185588, 108.4919086] -> NULL + needs_geocoding"""
    lat, lng, valid, needs_gc = sanitize_coordinates(-2.4185588, 108.4919086)
    assert lat is None
    assert lng is None
    assert valid is False
    assert needs_gc is True

def test_sanitize_coordinates_swapped():
    """Rule: Swapped lat/lng [111.9075, -8.0674] -> auto-swap to [-8.0674, 111.9075]"""
    lat, lng, valid, needs_gc = sanitize_coordinates(111.907519, -8.067420)
    assert lat == -8.06742
    assert lng == 111.907519
    assert valid is True
    assert needs_gc is False

def test_sanitize_coordinates_out_of_bounds_jakarta():
    """Rule: Jakarta/luar Jatim daratan -> NULL + needs_geocoding"""
    lat, lng, valid, needs_gc = sanitize_coordinates(-6.2088, 106.8456)
    assert lat is None
    assert valid is False
    assert needs_gc is True

def test_sanitize_coordinates_bawean_valid():
    """Rule v3.0: Pulau Bawean (lat ~-5.84, lng ~112.66) is VALID with expanded bbox"""
    lat, lng, valid, needs_gc = sanitize_coordinates(-5.848, 112.661)
    assert lat == -5.848
    assert lng == 112.661
    assert valid is True
    assert needs_gc is False

def test_sanitize_coordinates_kangean_valid():
    """Rule v3.0: Kepulauan Kangean (lat ~-6.9, lng ~115.4) is VALID with expanded bbox"""
    lat, lng, valid, needs_gc = sanitize_coordinates(-6.9, 115.4)
    assert valid is True
    assert needs_gc is False

def test_expanded_bounding_box_constants():
    """Verify v3.0 expanded bounding box includes Bawean & Kangean"""
    assert JATIM_LAT_MAX == -5.7
    assert JATIM_LNG_MAX == 116.6

# ===== Text & Phone Normalization Tests =====

def test_normalize_text_clean():
    dirty = "Jl. Raya Darmo No. 1 \r\n\t Surabaya   "
    assert normalize_text_clean(dirty) == "Jl. Raya Darmo No. 1 Surabaya"

def test_normalize_telepon_trailing_underscore():
    assert normalize_telepon("081333666651_ \r\n") == "081333666651"

def test_normalize_telepon_double_space():
    assert normalize_telepon("0341  792273") == "0341 792273"

def test_normalize_telepon_masking_preserved():
    """Masking **** from SIRS source should be preserved"""
    assert normalize_telepon("+623****2223") == "+623****2223"

def test_normalize_telepon_trailing_dash():
    assert normalize_telepon("031 - 8539671--") == "031 - 8539671"

def test_normalize_nama_rs_trailing_space():
    assert normalize_nama_rs("RS Umum Karsa Husada Kota Batu ") == "RS Umum Karsa Husada Kota Batu"

# ===== Ownership Normalization Tests (17 categories -> 4 enums) =====

def test_normalize_kepemilikan_pemerintah():
    assert normalize_kepemilikan("Pemkab") == "pemerintah"
    assert normalize_kepemilikan("Pemkot") == "pemerintah"
    assert normalize_kepemilikan("Pemprop") == "pemerintah"
    assert normalize_kepemilikan("Kemkes") == "pemerintah"
    assert normalize_kepemilikan("Kementerian Lain") == "pemerintah"
    assert normalize_kepemilikan("BUMN") == "pemerintah"

def test_normalize_kepemilikan_swasta():
    assert normalize_kepemilikan("SWASTA/LAINNYA") == "swasta"
    assert normalize_kepemilikan("Perusahaan") == "swasta"
    assert normalize_kepemilikan("Perorangan") == "swasta"
    assert normalize_kepemilikan("Organisasi Islam") == "swasta"
    assert normalize_kepemilikan("Organisasi Katholik") == "swasta"
    assert normalize_kepemilikan("Organisasi Protestan") == "swasta"
    assert normalize_kepemilikan("Organisasi Sosial") == "swasta"

def test_normalize_kepemilikan_tni_polri():
    assert normalize_kepemilikan("TNI AD") == "tni_polri"
    assert normalize_kepemilikan("TNI AL") == "tni_polri"
    assert normalize_kepemilikan("TNI AU") == "tni_polri"
    assert normalize_kepemilikan("POLRI") == "tni_polri"

# ===== Full Quality Gate Pipeline Test =====

def test_quality_gate_v3_pipeline():
    """Full pipeline test with v3.0 rules: dummy, swapped, Bawean valid, Jakarta null"""
    raw_rs = [
        {
            "kode": "3578001",
            "nama": "RS Siloam Surabaya \r\n",
            "alamat": "Jl. Raya Gubeng \t",
            "TELEPON": "031-5031333_",
            "koordinat": [-7.2712, 112.7485],
            "kelas": "B",
            "jenis": "RSU"
        },
        {
            "kode": "3525087",
            "nama": "RS Denisa ",
            "alamat": "Gresik",
            "TELEPON": "031-1234",
            "koordinat": [-2.4185588, 108.4919086],  # Dummy Kemenkes
            "kelas": "C",
            "jenis": "RSU"
        },
        {
            "kode": "3504068",
            "nama": "RS Umum Bhayangkara Tulungagung",
            "alamat": "Tulungagung",
            "TELEPON": "0355-1234",
            "koordinat": [111.9075, -8.0674],  # Swapped
            "kelas": "B",
            "jenis": "RSU"
        },
        {
            "kode": "3525101",
            "nama": "RS Umum Daerah Umar Mas'ud Bawean",
            "alamat": "Pulau Bawean",
            "TELEPON": "031-9999",
            "koordinat": [-5.848, 112.661],  # Bawean - VALID in v3.0
            "kelas": "D",
            "jenis": "RSU"
        },
        {
            "kode": "3515141",
            "nama": "RS Umum Bunda",
            "alamat": "Sidoarjo",
            "TELEPON": "031-8888",
            "koordinat": [-4.079, 119.997],  # Sulawesi - OUT OF BOUNDS
            "kelas": "C",
            "jenis": "RSU"
        }
    ]

    raw_rekap = [
        {"kode": "3578001", "pemilik": "Pemkot"},
        {"kode": "3525087", "pemilik": "SWASTA/LAINNYA"},
        {"kode": "3504068", "pemilik": "POLRI"},
        {"kode": "3525101", "pemilik": "Pemkab"},
        {"kode": "3515141", "pemilik": "Perusahaan"}
    ]

    df = clean_and_validate_hospitals(raw_rs, raw_rekap)
    assert len(df) == 5

    # RS 1: Valid Surabaya
    r1 = df[df["kode_rs"] == "3578001"].iloc[0]
    assert r1["nama_rs"] == "RS Siloam Surabaya"
    assert r1["telepon"] == "031-5031333"
    assert r1["is_valid_coord"] == 1
    assert r1["needs_geocoding"] == 0
    assert r1["kepemilikan"] == "pemerintah"
    assert r1["pemilik_raw"] == "Pemkot"

    # RS 2: Dummy Kemenkes -> NULL coords + needs_geocoding
    r2 = df[df["kode_rs"] == "3525087"].iloc[0]
    assert pd.isna(r2["lat"])
    assert r2["is_valid_coord"] == 0
    assert r2["needs_geocoding"] == 1
    assert r2["nama_rs"] == "RS Denisa"  # trailing space stripped

    # RS 3: Swapped -> auto-fixed
    r3 = df[df["kode_rs"] == "3504068"].iloc[0]
    assert r3["lat"] == -8.0674
    assert r3["lng"] == 111.9075
    assert r3["is_valid_coord"] == 1
    assert r3["kepemilikan"] == "tni_polri"

    # RS 4: Bawean -> VALID in v3.0 expanded bbox
    r4 = df[df["kode_rs"] == "3525101"].iloc[0]
    assert r4["lat"] == -5.848
    assert r4["lng"] == 112.661
    assert r4["is_valid_coord"] == 1
    assert r4["needs_geocoding"] == 0

    # RS 5: Sulawesi -> OUT OF BOUNDS -> NULL + needs_geocoding
    r5 = df[df["kode_rs"] == "3515141"].iloc[0]
    assert pd.isna(r5["lat"])
    assert r5["is_valid_coord"] == 0
    assert r5["needs_geocoding"] == 1
    assert r5["kepemilikan"] == "swasta"

def test_no_newline_in_cleaned_alamat():
    """Assert 0 alamat mengandung \\r\\n after cleaning"""
    raw_rs = [
        {"kode": "3509001", "nama": "RS Test", "alamat": "Jl. Thamrin No.31\r\n", "koordinat": [-7.5, 112.0], "kelas": "C", "jenis": "RSU"},
        {"kode": "3509002", "nama": "RS Test2", "alamat": "   Jl. Hasanudin No.98  ", "koordinat": [-7.6, 112.1], "kelas": "D", "jenis": "RSU"}
    ]
    df = clean_and_validate_hospitals(raw_rs)
    for _, row in df.iterrows():
        if row["alamat"]:
            assert "\r" not in row["alamat"]
            assert "\n" not in row["alamat"]
            assert not row["alamat"].startswith(" ")
            assert not row["alamat"].endswith(" ")
