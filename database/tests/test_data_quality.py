import pytest
import math
import pandas as pd
from pipeline.cleaner import (
    sanitize_coordinates,
    normalize_text_clean,
    normalize_telepon,
    normalize_nama_rs,
    clean_and_validate_hospitals
)

def test_sanitize_coordinates_dummy():
    # Rule: Dummy coordinate [-2.4185588, 108.4919086] must return None, None, False
    lat, lng, valid = sanitize_coordinates(-2.4185588, 108.4919086)
    assert lat is None
    assert lng is None
    assert valid is False

def test_sanitize_coordinates_swapped():
    # Rule: Swapped lat/lng (e.g. [111.9075, -8.0674]) must be auto-swapped back to [-8.0674, 111.9075]
    lat, lng, valid = sanitize_coordinates(111.907519, -8.067420)
    assert lat == -8.06742
    assert lng == 111.907519
    assert valid is True

def test_sanitize_coordinates_out_of_bounds():
    # Rule: Jakarta or abroad coordinates must return None, None, False
    lat, lng, valid = sanitize_coordinates(-6.2088, 106.8456)
    assert lat is None
    assert lng is None
    assert valid is False

def test_normalize_text_and_telepon():
    # Rule: clean \r\n and trailing underscores
    dirty_text = "Jl. Raya Darmo No. 1 \r\n\t Surabaya   "
    assert normalize_text_clean(dirty_text) == "Jl. Raya Darmo No. 1 Surabaya"

    dirty_phone = "081333666651_ \r\n"
    assert normalize_telepon(dirty_phone) == "081333666651"

    dirty_phone_2 = "031 - 8539671--"
    assert normalize_telepon(dirty_phone_2) == "031 - 8539671"

def test_quality_gate_clean_pipeline():
    raw_rs = [
        {
            "kode": "3578001",
            "nama": "RS Siloam Surabaya \r\n",
            "alamat": "Jl. Raya Gubeng \t",
            "TELEPON": "031-5031333_",
            "koordinat": [-7.2712, 112.7485], # Valid Jatim
            "kelas": "B"
        },
        {
            "kode": "3578002",
            "nama": "RS Dummy Laut",
            "alamat": "Unknown",
            "TELEPON": "08123456",
            "koordinat": [-2.4185588, 108.4919086], # Dummy
            "kelas": "C"
        },
        {
            "kode": "3504012",
            "nama": "RS Swapped Coord",
            "alamat": "Tulungagung",
            "TELEPON": "0355-1234",
            "koordinat": [111.9075, -8.0674], # Swapped
            "kelas": "B"
        }
    ]

    df = clean_and_validate_hospitals(raw_rs)
    assert len(df) == 3

    # Check RS 1
    r1 = df[df["kode_rs"] == "3578001"].iloc[0]
    assert r1["nama_rs"] == "RS Siloam Surabaya"
    assert r1["telepon"] == "031-5031333"
    assert bool(r1["is_valid_coord"]) is True

    # Check RS 2 (Dummy nullified)
    r2 = df[df["kode_rs"] == "3578002"].iloc[0]
    assert pd.isna(r2["lat"])
    assert pd.isna(r2["lng"])
    assert bool(r2["is_valid_coord"]) is False

    # Check RS 3 (Swapped fixed)
    r3 = df[df["kode_rs"] == "3504012"].iloc[0]
    assert r3["lat"] == -8.0674
    assert r3["lng"] == 111.9075
    assert bool(r3["is_valid_coord"]) is True
