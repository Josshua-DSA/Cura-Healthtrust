"""
Early Warning Alert Rule Evaluator Engine — PRD v3.0 F-EW01 & F-EW02.
Mengevaluasi kondisi data wilayah terhadap tabel alert_rules dan menghasilkan alert_events.
"""

import os
import json
import logging
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger("AlertEngine")


def evaluate_active_alerts(exports_dir: str) -> pd.DataFrame:
    """
    Evaluates district data against rules:
    - Bed Ratio Deficit (< 1.0 per 1000)
    - Stunting Prevalence (> 20%)
    - Surveillance Spike (Delta >= 50%)
    - Doctor Deficit (< 0.4 per 1000)
    """
    ml_path = os.path.join(exports_dir, "ml_readiness_dataset.parquet")
    surv_path = os.path.join(exports_dir, "disease_surveillance_weekly.parquet")
    kia_path = os.path.join(exports_dir, "maternal_child_health.parquet")

    events = []

    # 1. Evaluate from ML / Ratio store
    if os.path.exists(ml_path):
        df_ml = pd.read_parquet(ml_path)
        for _, row in df_ml.iterrows():
            kode = str(row["kode_bps"])
            nama = str(row["nama_wilayah"])
            rasio_tt = float(row.get("rasio_tt_proyeksi_2026", 0.0))
            rasio_doc = float(row.get("rasio_dokter_per_1000", 0.0))

            if rasio_tt < 1.0:
                events.append({
                    "rule_kode": "rasio_tt_defisit",
                    "kode_bps": kode,
                    "nama_wilayah": nama,
                    "nilai_terdeteksi": rasio_tt,
                    "pesan": f"Rasio tempat tidur {nama} ({rasio_tt:.2f} per 1.000) berada di bawah standar minimal WHO (1.0).",
                    "severity": "waspada",
                    "status": "active"
                })

            if rasio_doc < 0.4:
                events.append({
                    "rule_kode": "defisit_dokter",
                    "kode_bps": kode,
                    "nama_wilayah": nama,
                    "nilai_terdeteksi": rasio_doc,
                    "pesan": f"Rasio dokter umum {nama} ({rasio_doc:.2f} per 1.000) tergolong defisit kritis.",
                    "severity": "waspada",
                    "status": "active"
                })

    # 2. Evaluate from KIA store
    if os.path.exists(kia_path):
        df_kia = pd.read_parquet(kia_path)
        for _, row in df_kia.iterrows():
            kode = str(row["kode_bps"])
            nama = str(row["nama_wilayah"])
            stunting = float(row.get("prevalensi_stunting", 0.0))

            if stunting > 20.0:
                events.append({
                    "rule_kode": "stunting_tinggi",
                    "kode_bps": kode,
                    "nama_wilayah": nama,
                    "nilai_terdeteksi": stunting,
                    "pesan": f"Prevalensi stunting di {nama} ({stunting:.1f}%) melebihi ambang batas aman WHO 20%.",
                    "severity": "waspada",
                    "status": "active"
                })

    # 3. Evaluate from Surveillance store
    if os.path.exists(surv_path):
        df_surv = pd.read_parquet(surv_path)
        spike_df = df_surv[df_surv["status_surveillance"] == "perhatian"]
        for _, row in spike_df.iterrows():
            kode = str(row["kode_bps"])
            nama = str(row["nama_wilayah"])
            penyakit = str(row["nama_penyakit"])
            delta = float(row.get("delta_persen", 0.0))
            kasus = int(row.get("kasus_bulan_ini", 0))

            events.append({
                "rule_kode": "lonjakan_kasus_klb",
                "kode_bps": kode,
                "nama_wilayah": nama,
                "nilai_terdeteksi": delta,
                "pesan": f"Lonjakan kasus {penyakit} di {nama}: naik +{delta:.1f}% ({kasus} kasus) dalam 1 bulan terakhir.",
                "severity": "kritis",
                "status": "active"
            })

    df_events = pd.DataFrame(events) if events else pd.DataFrame(columns=[
        "rule_kode", "kode_bps", "nama_wilayah", "nilai_terdeteksi", "pesan", "severity", "status"
    ])

    out_csv = os.path.join(exports_dir, "active_alerts.csv")
    out_parquet = os.path.join(exports_dir, "active_alerts.parquet")
    df_events.to_csv(out_csv, index=False)
    try:
        df_events.to_parquet(out_parquet, index=False)
        logger.info(f"[AlertEngine] Triggered {len(df_events)} active alerts -> {out_parquet}")
    except Exception as e:
        logger.info(f"[AlertEngine] Saved active alerts to CSV (parquet skipped: {e})")

    return df_events
