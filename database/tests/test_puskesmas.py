import os
import pytest
import pandas as pd
from pipeline.loader import get_session
from models import FaskesPuskesmas, EnumTipeRawatPuskesmas
from etl.transform.clean_puskesmas import clean_and_validate_puskesmas, CleanPuskesmasSchema


def test_puskesmas_clean_schema_validation():
    sample_records = [
        {
            "kode_puskesmas": "PKM35780001",
            "nama": "Puskesmas Tegalsari",
            "tipe_rawat": "rawat_inap",
            "alamat": "Jl. Dinoyo No. 1, Kota Surabaya",
            "kode_bps": "3578",
            "kecamatan": "Tegalsari",
            "telepon": "031-567890",
            "jumlah_tt": 15,
            "lat": -7.280000,
            "lng": 112.740000,
            "source_id": "opendata_jatim",
            "coverage_periode": "2024-OFFICIAL"
        },
        {
            "kode_puskesmas": "PKM35780002",
            "nama": "Puskesmas Kedungdoro",
            "tipe_rawat": "non_rawat_inap",
            "alamat": "Jl. Kedungdoro No. 2, Kota Surabaya",
            "kode_bps": "3578",
            "kecamatan": "Tegalsari",
            "telepon": "031-567891",
            "jumlah_tt": 0,
            "lat": -7.265000,
            "lng": 112.735000,
            "source_id": "opendata_jatim",
            "coverage_periode": "2024-OFFICIAL"
        }
    ]
    df_clean = clean_and_validate_puskesmas(sample_records)
    assert len(df_clean) == 2
    assert (df_clean["is_valid_coord"] == 1).all()
    assert df_clean.iloc[0]["tipe_rawat"] == "rawat_inap"
    assert df_clean.iloc[1]["tipe_rawat"] == "non_rawat_inap"


def test_puskesmas_parquet_and_csv_export_existence():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    csv_path = os.path.join(exports_dir, "puskesmas_clean.csv")
    parquet_path = os.path.join(exports_dir, "puskesmas_clean.parquet")

    assert os.path.exists(csv_path), "puskesmas_clean.csv missing"
    assert os.path.exists(parquet_path), "puskesmas_clean.parquet missing"

    df = pd.read_parquet(parquet_path)
    assert len(df) >= 900
    assert "kode_puskesmas" in df.columns
    assert "tipe_rawat" in df.columns
    assert set(df["tipe_rawat"].unique()).issubset({"rawat_inap", "non_rawat_inap"})


def test_puskesmas_database_ingestion():
    session = get_session()
    try:
        count = session.query(FaskesPuskesmas).count()
        assert count >= 900, f"Expected >= 900 puskesmas in DB, got {count}"

        rawat_inap_count = session.query(FaskesPuskesmas).filter_by(tipe_rawat=EnumTipeRawatPuskesmas.rawat_inap).count()
        non_rawat_inap_count = session.query(FaskesPuskesmas).filter_by(tipe_rawat=EnumTipeRawatPuskesmas.non_rawat_inap).count()

        assert rawat_inap_count > 0
        assert non_rawat_inap_count > 0
        assert rawat_inap_count + non_rawat_inap_count == count
    finally:
        session.close()
