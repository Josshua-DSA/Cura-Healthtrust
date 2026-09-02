import os
import pytest
import pandas as pd
from pipeline.loader import get_session
from models import IndikatorKia, PenyakitSurveillance, AlertRule, AlertEvent


def test_kia_dataset_and_db():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "maternal_child_health.parquet")
    csv_path = os.path.join(exports_dir, "maternal_child_health.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df = pd.read_parquet(parquet_path)
    assert len(df) == 38  # 38 Kab/Kota
    assert "prevalensi_stunting" in df.columns
    assert "cakupan_idl" in df.columns
    assert "aki" in df.columns
    assert (df["prevalensi_stunting"] > 0).all()

    session = get_session()
    try:
        count = session.query(IndikatorKia).count()
        assert count == 38
    finally:
        session.close()


def test_surveillance_dataset_and_db():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "disease_surveillance_weekly.parquet")
    csv_path = os.path.join(exports_dir, "disease_surveillance_weekly.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df = pd.read_parquet(parquet_path)
    assert len(df) == 152  # 38 Kab/Kota * 4 Penyakit KLB
    assert set(df["status_surveillance"].unique()).issubset({"normal", "waspada", "perhatian"})
    assert "A90" in df["kode_icd10"].values

    session = get_session()
    try:
        count = session.query(PenyakitSurveillance).count()
        assert count == 152
    finally:
        session.close()


def test_alert_rules_and_active_events():
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    parquet_path = os.path.join(exports_dir, "active_alerts.parquet")
    csv_path = os.path.join(exports_dir, "active_alerts.csv")

    assert os.path.exists(parquet_path)
    assert os.path.exists(csv_path)

    df = pd.read_parquet(parquet_path)
    assert len(df) > 0
    assert "rule_kode" in df.columns
    assert "pesan" in df.columns
    assert "severity" in df.columns

    session = get_session()
    try:
        rules_count = session.query(AlertRule).count()
        events_count = session.query(AlertEvent).count()
        assert rules_count >= 5
        assert events_count > 0
    finally:
        session.close()
