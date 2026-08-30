# Modul Data Engineering & Database — Cura

Direktori ini berisi seluruh infrastruktur data pipeline, model PostgreSQL/PostGIS, modul ETL, skrip healthcheck, dataset ekspor, dan pengujian kualitas data (*Data Quality Gates*) untuk platform Cura — HealthTrust Jawa Timur.

---

## 📚 Navigasi Cepat Dokumentasi
* **[Kamus Data Lengkap & Resep Analisis (`DATA_DICTIONARY.md`)](DATA_DICTIONARY.md)**: Dokumentasi rinci seluruh kolom, tipe data, relasi foreign key, skema PostGIS, dan contoh kode analisis siap pakai untuk rekanan Data Analyst, ML, Backend, dan Frontend.
* **[README Utama Proyek (`../README.md`)](../README.md)**: Gambaran umum arsitektur proyek, fitur platform, quick-start guide, dan integrasi antar tim.

---

## 🛠️ Ringkasan Perintah CLI Runner

Jalankan perintah ini dari root direktori proyek dengan virtualenv aktif:

```bash
# 1. Healthcheck koneksi API eksternal & database
PYTHONPATH=database python database/cli.py check-health

# 2. Inisialisasi skema tabel, PostGIS extensions, indeks GIST & Views
PYTHONPATH=database python database/cli.py init-db

# 3. Seed referensi wilayah 38 Kab/Kota Jawa Timur
PYTHONPATH=database python database/cli.py seed-wilayah

# 4. Eksekusi Full End-to-End ETL Pipeline
PYTHONPATH=database python database/cli.py run-etl

# 5. Jalankan seluruh pengujian kualitas data (28 test cases)
PYTHONPATH=database pytest database/tests/ -v
```

---

## 📦 Output Dataset Bersih (`database/exports/`)
* `hospitals_clean.parquet` / `.csv`: Data 447 Rumah Sakit Jawa Timur tervalidasi.
* `bed_ratio_38_kab.parquet` / `.csv`: Rekap rasio ketercukupan tempat tidur 38 Kab/Kota standar WHO.
* `indicators_jatim.parquet` / `.csv`: Indikator tematik Puskesmas dan Tenaga Medis Dinkes Jatim 2024.
