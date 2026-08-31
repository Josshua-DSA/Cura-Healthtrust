# 🏥 Cura — HealthTrust Facilities Platform (Jawa Timur)

[![CI Pipeline](https://github.com/Josshua-DSA/Cura-Healthtrust/actions/workflows/ci.yml/badge.svg)](https://github.com/Josshua-DSA/Cura-Healthtrust/actions/workflows/ci.yml)
[![PostGIS](https://img.shields.io/badge/Database-PostgreSQL%2015%20%2B%20PostGIS%203.3-336791.svg?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Cura — HealthTrust Facilities** adalah platform analitik dan visualisasi data geospasial layanan fasilitas kesehatan (Faskes) terintegrasi untuk Provinsi Jawa Timur. Platform ini menggabungkan data operasional rumah sakit (SIRS Kemenkes), indikator kesehatan daerah (Open Data Jatim), dan batas administratif spasial (BPS/GIS) guna mendukung analisis ketercukupan tempat tidur rawat inap (standar WHO) serta pencarian faskes terdekat berbasis radius.

---

## 📑 Daftar Isi
1. [Fitur Utama & Keunggulan](#-fitur-utama--keunggulan)
2. [Arsitektur Sistem](#-arsitektur-sistem)
3. [Inventaris Data & Kamus Data Terstandarisasi](#-inventaris-data--kamus-data-terstandarisasi)
4. [Struktur Repositori](#-struktur-repositori)
5. [Panduan Memulai Cepat (Quick Start)](#-panduan-memulai-cepat-quick-start)
6. [Panduan Kolaborasi Antar-Jobdesk](#-panduan-kolaborasi-antar-jobdesk)
7. [Quality Gates & Automated CI](#-quality-gates--automated-ci)
8. [Lisensi & Kontribusi](#-lisensi--kontribusi)

---

## 🌟 Fitur Utama & Keunggulan

* 🗺️ **Peta Geospasial Interaktif (Choropleth & Clustering)**: Pemetaan ketercukupan faskes di 38 Kabupaten/Kota Jawa Timur dengan palet warna standar WHO (Hijau, Kuning, Merah).
* 📍 **PostGIS Spatial Radius Query**: Kemampuan pencarian faskes terdekat (`ST_DWithin` & `ST_Distance`) terindeks `GIST` dengan waktu respon sub-10ms.
* 🧹 **Automated Data Quality & Normalization**: Pembersihan otomatis terhadap koordinat anomali, eliminasi titik dummy Bangka Belitung, swap koordinat terbalik, dan normalisasi 17 kategori kepemilikan menjadi enum baku.
* 🚀 **Dual Export Ready (Parquet + CSV)**: File dataset bersih siap olah untuk Data Scientist/Analyst tanpa perlu konfigurasi database.
* 📊 **Precomputed Spatial Views**: View database `v_choropleth_wilayah` siap konsumsi untuk backend API tanpa JOIN berulang.

---

## 🏗️ Arsitektur Sistem

Platform mengadopsi arsitektur data engineering modern yang memisahkan lapisan data mentah, pembersihan berbasis kontrak skema, dan database spasial:

```text
  ┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
  │  SIRS Kemenkes REST API │    │  Open Data Jatim Portal │    │  Static Seeds (GeoJSON) │
  └────────────┬────────────┘    └────────────┬────────────┘    └────────────┬────────────┘
               │                              │                              │
               └──────────────────────────────┼──────────────────────────────┘
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │   1. Raw Ingestion & Snapshot Storage     │  --> database/raw/ (Retain 10)
                        └─────────────────────┬─────────────────────┘
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │   2. Data Quality & Pandera Validation    │  --> 28 Quality Gate Tests
                        │      - Dummy Coord Nullifier (OSM Geo)    │
                        │      - Swapped Lat/Lng Auto Fixer         │
                        │      - Ownership Enum Normalization       │
                        └─────────────────────┬─────────────────────┘
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │   3. Dual Export Pipeline (Ready-to-Use)  │  --> database/exports/ (*.parquet & *.csv)
                        └─────────────────────┬─────────────────────┘
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │   4. PostGIS 15 Spatial Database Engine   │
                        │      - ref_wilayah & tbl_rumah_sakit      │
                        │      - GIST Indexing & Spatial Views      │
                        └─────────────────────┬─────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌─────────────────────────┐                         ┌─────────────────────────┐
       │   FastAPI Backend API   │                         │ Analis & Data Scientist │
       │   (REST & GeoJSON API)  │                         │ (Jupyter / DuckDB / ML) │
       └────────────┬────────────┘                         └─────────────────────────┘
                    ▼
       ┌─────────────────────────┐
       │  Frontend Web Platform  │
       │   (Leaflet & ECharts)   │
       └─────────────────────────┘
```

---

## 📦 Inventaris Data & Kamus Data Terstandarisasi

Dataset bersih yang diekspor otomatis dan siap digunakan langsung oleh seluruh tim:

| File Dataset | Format | Deskripsi Singkat |
|---|---|---|
| `database/exports/hospitals_clean.*` | `.parquet` / `.csv` | 447 Rumah Sakit Jatim bersih, 3 enum kepemilikan, metadata `coverage_periode: 2026-LIVE`. |
| `database/exports/bed_ratio_38_kab.*` | `.parquet` / `.csv` | 38 Kab/Kota lengkap dengan rasio TT resmi Kemenkes + **Proyeksi Kependudukan BPS 2026**. |
| `database/exports/indicators_jatim.*` | `.parquet` / `.csv` | 114 baris indikator Puskesmas dan Dokter dari Dinkes Jatim 2024 (`2024-OFFICIAL`). |
| `database/seeds/jatim_districts.geojson`| `.geojson` | Batas polygon 38 Kab/Kota Jawa Timur (EPSG:4326). |

📖 **Dokumentasi Lengkap Kamus Data**:
Untuk penjelasan detail tipe data, nullable, relasi foreign key, dan contoh resep analisis kode Python/DuckDB, baca [**`database/DATA_DICTIONARY.md`**](database/DATA_DICTIONARY.md).

---

## 📁 Struktur Repositori

```text
HealthTrust/
├── .github/workflows/          # CI Pipeline GitHub Actions (PostGIS service + pytest)
├── database/                   # Layer Data Engineering & Database PostGIS
│   ├── config/                 # Konfigurasi database settings & data sources
│   ├── etl/                    # Modul transformer & loader data pipeline
│   │   ├── transform/          # Hospital & Spatial clean transformers
│   │   └── load/               # PostGIS atomic loader
│   ├── exports/                # Dataset bersih siap pakai (.parquet & .csv)
│   ├── health/                 # Healthcheck script API & database
│   ├── pipeline/               # Storage snapshot, crawler, cleaner, geocoder
│   ├── seeds/                  # Seed statis GeoJSON & referensi wilayah BPS
│   ├── tests/                  # Test suite data quality gates (28 tests)
│   ├── cli.py                  # CLI Master Runner pipeline database
│   ├── models.py               # Definisi Model ORM SQLAlchemy & PostGIS
│   ├── requirements.txt        # Dependensi Python layer database
│   └── DATA_DICTIONARY.md      # Kamus data lengkap & panduan query rekanan
├── experiments/                # Sandbox terisolasi untuk Data Analyst & Riset
│   ├── notebooks/              # Jupyter Notebooks untuk EDA & modeling
│   ├── data/                   # Data sementara analis
│   └── scripts/                # Script ad-hoc
├── docker-compose.yml          # Konfigurasi PostGIS (Port 5433) & Adminer (Port 8080)
├── README.md                   # Dokumentasi utama platform
└── .gitignore                  # Git hygiene rules
```

---

## 🚀 Panduan Memulai Cepat (Quick Start)

### 1. Prasyarat Sistem
* Python 3.11+
* Docker & Docker Compose

### 2. Setup Lingkungan & Database
```bash
# Clone repository
git clone https://github.com/Josshua-DSA/Cura-Healthtrust.git
cd Cura-Healthtrust

# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r database/requirements.txt

# Jalankan database PostGIS & Web GUI Adminer via Docker
docker-compose up -d
```

* Database PostgreSQL/PostGIS aktif di: `localhost:5433` (DB: `cura_db`, User: `cura_user`, Pass: `cura_password`).
* Web GUI Database (Adminer) aktif di: `http://localhost:8080`.

### 3. Eksekusi Data Pipeline
```bash
# Inisialisasi skema tabel, indeks spasial GIST, dan Spatial View
PYTHONPATH=database python database/cli.py init-db

# Seeding polygon wilayah 38 Kab/Kota
PYTHONPATH=database python database/cli.py seed-wilayah

# Jalankan full pipeline ETL (ingestion, sanitasi, geocoding, upsert, & export)
PYTHONPATH=database python database/cli.py run-etl

# Jalankan verifikasi seluruh test quality gates
PYTHONPATH=database pytest database/tests/ -v
```

---

## 👥 Panduan Kolaborasi Antar-Jobdesk

### 🔬 Tim Data Analyst & Machine Learning
* Langsung baca dataset dari `database/exports/hospitals_clean.parquet` tanpa perlu setup database.
* Gunakan folder `experiments/notebooks/` untuk membuat file notebook analisis/EDA tanpa risiko merusak pipeline produksi.
* Lihat contoh resep kode di [**`database/DATA_DICTIONARY.md`**](database/DATA_DICTIONARY.md).

### ⚙️ Tim Backend (FastAPI)
* Sambungkan aplikasi ke `postgresql+asyncpg://cura_user:cura_password@localhost:5433/cura_db`.
* Manfaatkan PostgreSQL Spatial View `v_choropleth_wilayah` untuk endpoint peta interaktif.
* Gunakan query radius PostGIS (`ST_DWithin`) untuk endpoint pencarian faskes terdekat.

### 🎨 Tim Frontend (Leaflet / Mapbox / ECharts)
* Gunakan batas wilayah polygon dari `database/seeds/jatim_districts.geojson`.
* Terapkan palet warna standar ketercukupan tempat tidur WHO:
  * 🟢 **Hijau**: `#2ECC71` (Rasio $\ge 1.0$)
  * 🟡 **Kuning**: `#F1C40F` (Rasio $0.7 - 0.99$)
  * 🔴 **Merah**: `#E74C3C` (Rasio $< 0.7$)

---

## 🛡️ Quality Gates & Automated CI

Setiap Pull Request yang diajukan ke branch `main` secara otomatis diverifikasi oleh GitHub Actions CI yang menjalankan **28 Quality Gate Tests**:
1. Sanitasi koordinat dummy Kemenkes menjadi `null`.
2. Deteksi & auto-swap koordinat terbalik.
3. Validasi batas geografis (Bounding Box Jatim mencakup Bawean & Kangean).
4. Pembersihan noise string pada alamat (`\r\n`) dan format telepon.
5. Standardisasi enum kepemilikan (`pemerintah`, `swasta`, `tni_polri`).
6. Verifikasi integritas relasi foreign key `ref_wilayah`.
7. Keberadaan dan integritas view spasial `v_choropleth_wilayah` & file Parquet.

---

## 📄 Lisensi
Proyek ini didistribusikan di bawah lisensi MIT.
