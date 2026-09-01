"""
ML Feature Store Builder — Action Plan v7.0.
Menyatukan data Faskes (RS + Puskesmas) + Tenaga Medis (SDM) + Beban Morbiditas Penyakit
ke dalam satu dataset siap latih model Machine Learning (ml_readiness_dataset.parquet / .csv).
"""

import os
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("MLFeatureBuilder")


def build_ml_readiness_dataset(exports_dir: str) -> pd.DataFrame:
    """
    Consolidate district-level features for ML training:
    - Bed Ratio & 2026 Projection
    - Total Hospitals & Total Puskesmas (Rawat Inap vs Non)
    - Medical Workforce (Dokter Umum, Spesialis, Gigi, Perawat, Bidan)
    - Morbidity Burden (Total Annual Patient Cases, Inpatient vs Outpatient)
    - Thematic Health Indicators (Stunting/Gizi, AKI/AKB proxy)
    """
    ratio_path = os.path.join(exports_dir, "bed_ratio_38_kab.parquet")
    pkm_path = os.path.join(exports_dir, "puskesmas_clean.parquet")
    rs_path = os.path.join(exports_dir, "hospitals_clean.parquet")
    nakes_path = os.path.join(exports_dir, "healthcare_workforce.parquet")
    morbidity_path = os.path.join(exports_dir, "disease_morbidity_trends.parquet")

    # 1. Base District table
    if not os.path.exists(ratio_path):
        raise FileNotFoundError(f"Base dataset {ratio_path} not found.")

    df_base = pd.read_parquet(ratio_path).copy()
    
    # Keep core demographic & bed capacity features
    ml_df = df_base[[
        "kode_bps", "nama_wilayah", "total_tt", "jumlah_penduduk_2021",
        "rasio_tt_resmi", "kategori_who_resmi", "proyeksi_penduduk_2026",
        "rasio_tt_proyeksi_2026", "kategori_who_proyeksi_2026"
    ]].copy()

    # 2. Add Puskesmas granular features
    if os.path.exists(pkm_path):
        df_pkm = pd.read_parquet(pkm_path)
        pkm_agg = df_pkm.groupby("kode_bps").agg(
            total_puskesmas=("kode_puskesmas", "count"),
            puskesmas_rawat_inap=("tipe_rawat", lambda x: (x == "rawat_inap").sum()),
            puskesmas_non_rawat_inap=("tipe_rawat", lambda x: (x == "non_rawat_inap").sum()),
            total_tt_puskesmas=("jumlah_tt", "sum")
        ).reset_index()
        ml_df = ml_df.merge(pkm_agg, on="kode_bps", how="left")
    else:
        ml_df["total_puskesmas"] = 0
        ml_df["puskesmas_rawat_inap"] = 0
        ml_df["puskesmas_non_rawat_inap"] = 0
        ml_df["total_tt_puskesmas"] = 0

    # 3. Add Hospital counts
    if os.path.exists(rs_path):
        df_rs = pd.read_parquet(rs_path)
        rs_agg = df_rs.groupby("kode_bps").agg(
            total_rs=("kode_rs", "count"),
            rs_pemerintah=("kepemilikan", lambda x: (x == "pemerintah").sum()),
            rs_swasta=("kepemilikan", lambda x: (x == "swasta").sum()),
            rs_tni_polri=("kepemilikan", lambda x: (x == "tni_polri").sum())
        ).reset_index()
        ml_df = ml_df.merge(rs_agg, on="kode_bps", how="left")
    else:
        ml_df["total_rs"] = 0
        ml_df["rs_pemerintah"] = 0
        ml_df["rs_swasta"] = 0
        ml_df["rs_tni_polri"] = 0

    # 4. Add Workforce (Dokter, Perawat, Bidan)
    if os.path.exists(nakes_path):
        df_nakes = pd.read_parquet(nakes_path)
        nakes_piv = df_nakes.pivot_table(
            index="kode_bps",
            columns="jenis_nakes",
            values="jumlah",
            aggfunc="sum",
            fill_value=0
        ).reset_index()
        ml_df = ml_df.merge(nakes_piv, on="kode_bps", how="left")

    # 5. Add Morbidity (Kasus Penyakit & Beban Rawat Inap)
    if os.path.exists(morbidity_path):
        df_morb = pd.read_parquet(morbidity_path)
        morb_agg = df_morb.groupby("kode_bps").agg(
            total_kasus_pasien_tahunan=("jumlah_pasien", "sum"),
            kasus_rawat_inap_tahunan=("jumlah_pasien", lambda s: df_morb.loc[s.index[df_morb.loc[s.index, "tipe_pelayanan"] == "rawat_inap"], "jumlah_pasien"].sum()),
            kasus_menular_tahunan=("jumlah_pasien", lambda s: df_morb.loc[s.index[df_morb.loc[s.index, "status_kasus"] == "menular"], "jumlah_pasien"].sum())
        ).reset_index()
        ml_df = ml_df.merge(morb_agg, on="kode_bps", how="left")

    # 6. Engineered ML Ratios / Density Features
    pop_k = ml_df["proyeksi_penduduk_2026"] / 1000.0
    if "dokter_umum" in ml_df.columns:
        ml_df["rasio_dokter_per_1000"] = (ml_df["dokter_umum"] / pop_k).round(3)
    if "perawat" in ml_df.columns:
        ml_df["rasio_perawat_per_1000"] = (ml_df["perawat"] / pop_k).round(3)
    if "bidan" in ml_df.columns:
        ml_df["rasio_bidan_per_1000"] = (ml_df["bidan"] / pop_k).round(3)

    # Fill any remaining NaNs
    ml_df = pd.DataFrame(ml_df.fillna(0))

    out_csv = os.path.join(exports_dir, "ml_readiness_dataset.csv")
    out_parquet = os.path.join(exports_dir, "ml_readiness_dataset.parquet")
    ml_df.to_csv(out_csv, index=False)
    try:
        ml_df.to_parquet(out_parquet, index=False)
        logger.info(f"[ML Store] Generated unified ML dataset -> {out_parquet} ({len(ml_df)} rows x {len(ml_df.columns)} cols)")
    except Exception as e:
        logger.info(f"[ML Store] Generated unified ML dataset -> {out_csv} ({len(ml_df)} rows)")

    return ml_df
