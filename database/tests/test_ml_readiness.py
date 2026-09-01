import os
import pytest
import pandas as pd
from pipeline.loader import get_session
from models import TblTenagaKesehatan, TblPasienPenyakitWilayah


def test_workforce_export_and_db_counts():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "healthcare_workforce.parquet")
    csv_path = os.path.join(exports_dir, "healthcare_workforce.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df = pd.read_parquet(parquet_path)
    assert len(df) == 266  # 38 Kab/Kota * 7 jenis nakes
    assert "dokter_umum" in df["jenis_nakes"].values
    assert "perawat" in df["jenis_nakes"].values
    assert (df["jumlah"] >= 0).all()

    session = get_session()
    try:
        count = session.query(TblTenagaKesehatan).count()
        assert count == 266
    finally:
        session.close()


def test_morbidity_trends_export_and_db_counts():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "disease_morbidity_trends.parquet")
    csv_path = os.path.join(exports_dir, "disease_morbidity_trends.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df = pd.read_parquet(parquet_path)
    assert len(df) == 1520  # 38 Kab/Kota * 4 Q * 10 Penyakit
    assert "Demam Berdarah Dengue (DBD)" in df["nama_penyakit"].values
    assert set(df["triwulan"].unique()) == {"Q1", "Q2", "Q3", "Q4"}

    session = get_session()
    try:
        count = session.query(TblPasienPenyakitWilayah).count()
        assert count == 1520
    finally:
        session.close()


def test_ml_readiness_unified_dataset():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "ml_readiness_dataset.parquet")
    csv_path = os.path.join(exports_dir, "ml_readiness_dataset.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df_ml = pd.read_parquet(parquet_path)
    assert len(df_ml) == 38  # 38 Kab/Kota
    # Feature columns check
    expected_cols = [
        "kode_bps", "nama_wilayah", "total_tt", "total_puskesmas",
        "total_rs", "dokter_umum", "perawat", "bidan",
        "total_kasus_pasien_tahunan", "rasio_dokter_per_1000",
        "proyeksi_penduduk_2026", "rasio_tt_proyeksi_2026"
    ]
    for col in expected_cols:
        assert col in df_ml.columns, f"Missing ML feature: {col}"

    assert (df_ml["total_rs"] > 0).all()
    assert (df_ml["total_puskesmas"] > 0).all()
    assert (df_ml["dokter_umum"] > 0).all()
    assert (df_ml["rasio_dokter_per_1000"] > 0).all()
