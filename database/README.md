# Modul Data Engineering & Database — Cura
> Layer Pengolahan Data, PostGIS Spasial, Sanitasi ETL, dan Ekspor Siap Pakai

Direktori ini berisi seluruh infrastruktur data pipeline, model PostgreSQL 15 + PostGIS 3.3, modul ETL (crawler, sanitasi, geocoder), skrip healthcheck, dataset ekspor, dan pengujian kualitas data (*Data Quality Gates*) untuk platform Cura — HealthTrust Jawa Timur.

---

## 👥 Panduan Kolaborasi Antar-Jobdesk

### 🔬 1. Tim Data Analyst & Machine Learning Engineer
* **Akses Data Tanpa Setup DB**: Langsung konsumsi file di `database/exports/` (`.parquet` dan `.csv`). Tidak perlu install PostgreSQL / PostGIS lokal.
* **Feature Store Siap Latih**: Gunakan `database/exports/ml_readiness_dataset.parquet` (38 baris Kab/Kota × 30 fitur numerik bersih, 0 missing value) untuk:
  - *Clustering Disparitas Layanan*: K-Means / DBSCAN pada rasio faskes dan tenaga medis.
  - *Bed Demand Forecasting*: Time-series / XGBoost prediksi kebutuhan ranjang rawat inap.
  - *Maternal Risk Scoring*: Random Forest + SHAP interpretability untuk faktor risiko stunting/AKI.
* **Sandbox Riset**: Gunakan folder `experiments/notebooks/` untuk membuat file Jupyter Notebook (`.ipynb`) atau script eksplorasi tanpa risiko merusak pipeline produksi.
* **Kamus Data**: Pelajari definisi kolom dan tipe data di [**`database/DATA_DICTIONARY.md`**](DATA_DICTIONARY.md).

### ⚙️ 2. Tim Backend Developer (FastAPI)
* **Koneksi Database**: Hubungkan backend ke PostgreSQL/PostGIS:
  `postgresql+asyncpg://cura_user:cura_password@localhost:5433/cura_db`
* **Spatial Precomputed Views**: Manfaatkan PostgreSQL Spatial View `v_choropleth_wilayah` dan `v_faskes_all` untuk endpoint peta interaktif dan katalog faskes tanpa beban join berulang di runtime.
* **Spatial Radius Query**: Gunakan fungsi PostGIS native (`ST_DWithin` & `ST_Distance`) untuk melayani endpoint pencarian faskes terdekat berbasis GPS/koordinat user.
* **AI Context Injection**: Manfaatkan data agregat `stat_wilayah` / `tbl_agregat_wilayah` sebagai konteks ringkas untuk endpoint `/api/v1/ask`.

### 🎨 3. Tim Frontend Developer (Public Web & Dashboard)
* **Batas Wilayah**: Gunakan GeoJSON batas wilayah 38 Kab/Kota dari `database/seeds/jatim_districts.geojson` untuk render layer choropleth di Leaflet.js / Mapbox.
* **Katalog & Filter**: Konsumsi endpoint backend `/api/v1/faskes` atau file `database/exports/hospitals_clean.csv` untuk katalog RS + Puskesmas dengan filter kelas (A/B/C/D), kepemilikan, dan jenis faskes.
* **Standar Palet Warna WHO**: Terapkan standar visualisasi berikut pada peta dan dashboard:
  - 🟢 **Hijau**: `#2ECC71` (Rasio $\ge 1.0$ tempat tidur per 1.000 penduduk — Ideal)
  - 🟡 **Kuning**: `#F1C40F` (Rasio $0.7 - 0.99$ — Rentan)
  - 🔴 **Merah**: `#E74C3C` (Rasio $< 0.7$ — Defisit Kritis)

---

## 🛠️ Panduan Eksekusi & CLI Runner

Jalankan perintah ini dari root direktori proyek dengan virtual environment aktif:

```bash
# 1. Healthcheck konektivitas sumber API eksternal & database
python3 database/cli.py check-health

# 2. Inisialisasi skema tabel, ekstensi PostGIS, indeks GIST, dan Spatial Views
python3 database/cli.py init-db

# 3. Seed referensi wilayah & GeoJSON 38 Kab/Kota Jawa Timur
python3 database/cli.py seed-wilayah

# 4. Eksekusi Full End-to-End ETL Pipeline (Ingestion, Sanitasi, Geocoding, & Export)
python3 database/cli.py run-etl

# 5. Jalankan seluruh pengujian kualitas data (41 unit tests)
pytest database/tests/ -v
```

---

## 📦 Inventaris Output Dataset Bersih (`database/exports/`)

| File Dataset | Format | Dimensi | Deskripsi & Cakupan |
|---|---|---|---|
| `hospitals_clean.*` | `.parquet` / `.csv` | 447 baris × 15 kolom | Seluruh RS aktif se-Jatim, 3 enum kepemilikan, koordinat sanitasi (`2026-LIVE`). |
| `puskesmas_clean.*` | `.parquet` / `.csv` | 977 baris × 8 kolom | Puskesmas Rawat Inap & Non Rawat Inap 38 Kab/Kota (`2024-OFFICIAL`). |
| `bed_ratio_38_kab.*` | `.parquet` / `.csv` | 38 baris × 10 kolom | Rasio tempat tidur resmi Kemenkes 2021 + Proyeksi Kependudukan BPS 2026. |
| `indicators_jatim.*` | `.parquet` / `.csv` | 114 baris × 9 kolom | Indikator Puskesmas, Dokter, dan Nakes Dinkes Jatim 2024. |
| `ml_readiness_dataset.*` | `.parquet` / `.csv` | 38 baris × 30 kolom | Feature store gabungan siap latih model (0 nulls). |

---

## 📖 Dokumentasi Terkait
* [**`DATA_DICTIONARY.md`**](DATA_DICTIONARY.md): Kamus data rinci setiap kolom, constraints, dan contoh kode Python/JS.
* [**`../context/SCHEMA.md`**](../context/SCHEMA.md): DDL SQL skema lengkap PostgreSQL 15 + PostGIS 3.3.
* [**`../context/AUDIT_AND_ACTION_PLAN.md`**](../context/AUDIT_AND_ACTION_PLAN.md): Log audit data, sanitasi anomali, dan action plan proyek.
