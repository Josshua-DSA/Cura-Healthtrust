# Cura — HealthTrust Facilities (Database & Data Engineering Layer)

Dokumentasi teknis khusus untuk modul `database/` dan pengelolaan data layer pada proyek Cura — HealthTrust. Dokumen ini menjelaskan arsitektur pipeline ETL, model skema PostGIS, panduan penggunaan CLI, fungsi-fungsi modular dalam kode Python, serta petunjuk integrasi untuk tim backend, frontend, analis data, dan penyusun proposal/PPT.

---

## 📑 Daftar Isi
1. [Arsitektur Data & Alur Pipeline](#1-arsitektur-data--alur-pipeline)
2. [Setup Lingkungan & Layanan Container](#2-setup-lingkungan--layanan-container)
3. [Panduan CLI Runner (Command-Line Interface)](#3-panduan-cli-runner-command-line-interface)
4. [Dokumentasi Fungsi & Modul Python (`database/`)](#4-dokumentasi-fungsi--modul-python-database)
   - [Pipeline Storage (`pipeline.storage`)](#pipeline-storage-pipelinestorage)
   - [Pipeline Cleaner & Data Contracts (`pipeline.cleaner` / `etl.transform.clean_hospitals`)](#pipeline-cleaner--data-contracts-pipelinecleaner--etltransformclean_hospitals)
   - [Spatial Cleaner & Ratio Calculator (`etl.transform.clean_spatial`)](#spatial-cleaner--ratio-calculator-etltransformclean_spatial)
   - [Open Data Jatim Crawler (`pipeline.opendata_crawler`)](#open-data-jatim-crawler-pipelineopendata_crawler)
   - [Database Loader & Spatial Upsert (`pipeline.loader` / `etl.load.load_to_postgis`)](#database-loader--spatial-upsert-pipelineloader--etlloadload_to_postgis)
   - [Audit Trail & Logging (`pipeline.audit`)](#audit-trail--logging-pipelineaudit)
   - [End-to-End Orchestrator (`pipeline.orchestrator`)](#end-to-end-orchestrator-pipelineorchestrator)
5. [Skema Tabel & Kamus Data Database](#5-skema-tabel--kamus-data-database)
6. [Panduan Konsumsi Data Antar-Jobdesk](#6-panduan-konsumsi-data-antar-jobdesk)
   - [Jobdesk Backend](#jobdesk-backend-fastapi--rest-api)
   - [Jobdesk Frontend](#jobdesk-frontend-leaflet--echarts)
   - [Jobdesk Analis / Riset (Sandbox)](#jobdesk-analis--riset-sandbox)
   - [Jobdesk Proposal & PPT](#jobdesk-proposal--ppt)
7. [Debugging & Pengujian Kualitas Data](#7-debugging--pengujian-kualitas-data)

---

## 1. Arsitektur Data & Alur Pipeline

Pipeline data mengadopsi pendekatan hybrid (REST API + CSV Ingestion) dengan 6 tahap pemrosesan otomatis:

```text
[SIRS Kemenkes REST API]     [Open Data Jatim Portal]     [Static Seeds (GeoJSON / CSV)]
          │                             │                               │
          └─────────────────────────────┼───────────────────────────────┘
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 1. Raw Ingestion & Snapshot Cache │  --> database/raw/{source}/{ts}.json
                      └───────────────────────────────────┘
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 2. Data Cleaning & Pandera Valid. │  --> Bounding Box Jatim (-8.8 s/d -6.7, 110.9 s/d 114.4)
                      └───────────────────────────────────┘  --> Swap swapped coords, nullify dummy coords
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 3. Export Clean Dataset (CSV)     │  --> database/exports/hospitals_clean.csv
                      └───────────────────────────────────┘
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 4. Idempotent PostGIS Upsert      │  --> ON CONFLICT DO UPDATE
                      └───────────────────────────────────┘  --> ST_SetSRID(ST_MakePoint(lng, lat), 4326)
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 5. Precompute Aggregates & WHO    │  --> tbl_agregat_wilayah (38 Kab/Kota)
                      └───────────────────────────────────┘
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │ 6. Write Pipeline Audit Trail     │  --> tbl_pipeline_log (Status: SUCCESS/FAILED)
                      └───────────────────────────────────┘
```

---

## 2. Setup Lingkungan & Layanan Container

### 2.1 Menyalakan Database PostgreSQL + PostGIS & Adminer
```bash
# Menjalankan container di background
docker-compose up -d

# Memeriksa status container
docker-compose ps
```
* **PostgreSQL + PostGIS**: `localhost:5433` (Port default diubah ke 5433 untuk mencegah konflik dengan Postgres lokal).
* **Adminer Web GUI**: `http://localhost:8080` (Akses visual ke tabel database).
  * System: `PostgreSQL` | Server: `postgres` | User: `cura_user` | Pass: `cura_password` | DB: `cura_db`

### 2.2 Menyiapkan Virtual Environment Python
```bash
# Buat dan aktifkan virtual environment di root direktori
python3 -m venv .venv
source .venv/bin/activate

# Install dependensi
pip install -r database/requirements.txt
```

---

## 3. Panduan CLI Runner (Command-Line Interface)

Seluruh operasi data layer dikendalikan melalui satu entry point CLI: `database/cli.py`.

```bash
# 1. Cek kesehatan koneksi semua API eksternal dan PostgreSQL/PostGIS
PYTHONPATH=database python database/cli.py check-health

# 2. Inisialisasi tabel, tipe enum, dan index spasial GIST di PostgreSQL
PYTHONPATH=database python database/cli.py init-db

# 3. Seed data referensi awal 38 Kabupaten/Kota Jawa Timur
PYTHONPATH=database python database/cli.py seed-wilayah

# 4. Eksekusi Full ETL Pipeline (Fetch -> Clean -> Validate -> Upsert -> Aggregate -> Export)
PYTHONPATH=database python database/cli.py run-etl

# 5. Jalankan Automated Scheduler Daemon (Default: Tiap Senin 07:00 WIB)
PYTHONPATH=database python database/cli.py scheduler

# 6. Menjalankan scheduler dengan opsi kustom (misal: harian pukul 03:00 subuh)
PYTHONPATH=database python database/cli.py scheduler --day daily --hour 3 --minute 0

# 7. Menjalankan seluruh test suite unit test & data quality gates
PYTHONPATH=database python database/cli.py test-db
```

---

## 4. Dokumentasi Fungsi & Modul Python (`database/`)

Modul-modul di `database/pipeline/` dirancang modular dan reusable. Berikut cara import dan pemanggilan fungsinya di script atau notebook lain:

### Pipeline Storage (`pipeline.storage`)
Mengelola penyimpanan data mentah (snapshot caching) dan fallback saat API offline.

```python
from pipeline.storage import save_raw_snapshot, load_latest_snapshot

# 1. Menyimpan respons data mentah dari API ke folder database/raw/
snapshot_path = save_raw_snapshot(
    source_id="sirs_kemenkes_list",
    data={"rs": [...]} # Dict atau List data mentah
)
# Output: database/raw/sirs_kemenkes_list/YYYYMMDD_HHMMSS.json + latest.json

# 2. Membaca snapshot data mentah terakhir (fallback saat API offline)
data, file_path = load_latest_snapshot("sirs_kemenkes_list")
if data:
    print(f"Loaded {len(data['rs'])} records from {file_path}")
```

---

### Pipeline Cleaner & Data Contracts (`pipeline.cleaner`)
Membersihkan data string, menangani anomali koordinat spasial, dan memvalidasi struktur data dengan Pandera.

```python
from pipeline.cleaner import (
    clean_and_validate_hospitals,
    sanitize_coordinates,
    normalize_text_clean,
    normalize_telepon,
    normalize_nama_rs,
    normalize_kelas,
    normalize_kepemilikan,
    extract_kode_bps_from_kode_rs
)

# 1. Pembersihan koordinat spasial (menangani dummy Kemenkes & swapped lat/lng)
# Aturan:
# - Dummy laut Bangka Belitung [-2.4185588, 108.4919086] -> (None, None, False)
# - Swapped [111.90, -8.06] -> (-8.06, 111.90, True)
# - Di luar Bounding Box Jatim (-8.8 s/d -6.7, 110.9 s/d 114.4) -> (None, None, False)
lat, lng, is_valid = sanitize_coordinates(111.907519, -8.067420)
# Output: (-8.06742, 111.907519, True)

# 2. Pembersihan teks dan nomor telepon
clean_alamat = normalize_text_clean("Jl. Raya Darmo No. 1 \r\n\t Surabaya   ")
# Output: "Jl. Raya Darmo No. 1 Surabaya"

clean_phone = normalize_telepon("081333666651_ \r\n")
# Output: "081333666651"

# 3. Normalisasi enum kelas dan kepemilikan
kelas_enum = normalize_kelas("B")           # Output: "B"
pemilik_enum = normalize_kepemilikan("TNI AD") # Output: "tni_polri"

# 4. Ekstraksi kode BPS dari ID RS
kode_bps = extract_kode_bps_from_kode_rs("3578011") # Output: "3578" (Surabaya)

# 5. Full dataframe cleaning & Pandera validation
df_clean = clean_and_validate_hospitals(raw_rs_list, raw_rekap_list)
# Mengembalikan pd.DataFrame yang lolos skema CleanHospitalSchema
```

---

### Spatial Cleaner & Ratio Calculator (`etl.transform.clean_spatial`)
Memvalidasi polygon GeoJSON wilayah dan menyusun dataframe rasio tempat tidur WHO per 38 Kab/Kota.

```python
from etl.transform.clean_spatial import clean_and_validate_districts

# Validasi polygon & hitung ringkasan rasio TT per 1.000 penduduk
district_records, df_ratio = clean_and_validate_districts(geojson_raw, rasio_tt_raw)
# district_records: List[Dict] siap upsert ke ref_wilayah (PostGIS Polygon)
# df_ratio: pd.DataFrame (kode_bps, nama_wilayah, total_tt, jumlah_penduduk, rasio_tt_per_1000, kategori_who)
```

---

### Open Data Jatim Crawler (`pipeline.opendata_crawler`)
Mengambil data indikator tematik dan memetakan nama wilayah ke kode BPS 4 digit.

```python
from pipeline.opendata_crawler import match_kode_bps, crawl_and_parse_opendata_csv

# 1. Fuzzy match nama daerah ke kode BPS resmi (3501 - 3579)
kode_1 = match_kode_bps("Kabupaten Pacitan") # Output: "3501"
kode_2 = match_kode_bps("Kota Surabaya")     # Output: "3578"
kode_3 = match_kode_bps("surabaya")          # Output: "3578"

# 2. Crawl dan parsing indikator kesehatan Open Data Jatim (Puskesmas, Dokter, dll)
records = crawl_and_parse_opendata_csv()
# Mengembalikan List[Dict] siap upsert ke tbl_indikator_kesehatan
```

---

### Database Loader & Spatial Upsert (`pipeline.loader`)
Menyediakan sesi database SQLAlchemy dan query upsert idempoten ke PostGIS.

```python
from pipeline.loader import (
    get_session,
    init_db,
    upsert_rumah_sakit,
    upsert_ref_wilayah,
    upsert_penduduk,
    upsert_indikator_kesehatan,
    recompute_agregat_wilayah,
    generate_rs_key
)

# 1. Inisialisasi koneksi session DB
session = get_session()

# 2. Inisialisasi tabel dan index GIST PostGIS
init_db()

# 3. Upsert data RS (idempoten dengan ST_SetSRID Point 4326)
count_rs = upsert_rumah_sakit(session, records=df_clean.to_dict(orient="records"))

# 4. Upsert indikator kesehatan
count_ind = upsert_indikator_kesehatan(session, records=records)

# 5. Pre-compute agregat 38 Kab/Kota & rasio WHO
count_aggr = recompute_agregat_wilayah(session, tahun=2024)

# Tutup session setelah selesai
session.close()
```

---

### Audit Trail & Logging (`pipeline.audit`)
Mencatat metadata setiap run pipeline ke tabel `tbl_pipeline_log`.

```python
from pipeline.audit import start_pipeline_log, finish_pipeline_log
from models import EnumPipelineStatus

session = get_session()

# 1. Catat awal eksekusi pipeline
log_entry = start_pipeline_log(session, source_id="full_etl_sirs_kemenkes")
log_id = log_entry.id

# 2. Catat status selesai (SUCCESS / FAILED)
finish_pipeline_log(
    session=session,
    log_id=log_id,
    status=EnumPipelineStatus.SUCCESS,
    record_extracted=447,
    record_loaded=561,
    error_message=None
)
session.close()
```

---

### End-to-End Orchestrator (`pipeline.orchestrator`)
Fungsi utama yang merangkai seluruh alur ingestion, cleaning, export, loading, agregasi, dan logging dalam satu eksekusi atomic.

```python
from pipeline.orchestrator import execute_full_etl

# Eksekusi full ETL secara programatik
result = execute_full_etl()
print(result)
# Output: {'status': 'SUCCESS', 'extracted': 447, 'loaded': 561}
```

---

## 5. Skema Tabel & Kamus Data Database

Database menggunakan PostgreSQL 15 + PostGIS 3.3 (`cura_db`).

### 1. `ref_wilayah` (Tabel Dimensi Wilayah)
| Kolom | Tipe | Keterangan |
|---|---|---|
| `kode_bps` | `VARCHAR(4)` (PK) | Kode BPS 4 digit (contoh: `3578` untuk Kota Surabaya). |
| `nama_wilayah` | `VARCHAR(100)` | Nama resmi kabupaten/kota. |
| `tipe` | `enum_tipe_wilayah` | Nilai: `KABUPATEN` atau `KOTA`. |
| `geom` | `geometry(MULTIPOLYGON, 4326)` | Batas polygon spasial wilayah (Indeks `GIST`). |

### 2. `tbl_rumah_sakit` (Tabel Fakta Fasilitas Kesehatan)
| Kolom | Tipe | Keterangan |
|---|---|---|
| `kode_rs` | `VARCHAR(50)` (PK/Unique) | Kode resmi SIRS Kemenkes (contoh: `3578011`) atau deterministik hash. |
| `nama_rs` | `VARCHAR(255)` | Nama rumah sakit (sudah dibersihkan). |
| `alamat` | `TEXT` | Alamat faskes. |
| `kode_bps` | `VARCHAR(4)` (FK) | Relasi ke `ref_wilayah.kode_bps`. |
| `kelas` | `enum_kelas_rs` | Nilai: `A`, `B`, `C`, `D`, `tidak_diketahui`. |
| `kepemilikan` | `enum_kepemilikan` | Nilai: `pemerintah`, `swasta`, `tni_polri`, `lainnya`. |
| `pemilik_raw` | `VARCHAR(50)` | Nilai mentah kepemilikan SIRS sebelum mapping enum (audit trail). |
| `jenis_rs` | `VARCHAR(50)` | Jenis faskes: `RSU`, `RSIA`, `RSK Mata`, `RSK Bedah`, dll. |
| `jumlah_tt` | `INTEGER` | Jumlah kapasitas tempat tidur operasional. |
| `telepon` | `VARCHAR(50)` | Nomor telepon (sudah dibersihkan dari trailing noise). |
| `lat` / `lng` | `FLOAT` | Titik koordinat desimal (bernilai `NULL` jika koordinat dummy/anomali). |
| `geom` | `geometry(POINT, 4326)` | Titik spasial PostGIS untuk query radius (Indeks `GIST`). |
| `is_valid_coord` | `INTEGER` | Flag validasi koordinat: `1` = valid, `0` = dummy/OOB/null. |
| `needs_geocoding` | `INTEGER` | Flag geocoding: `1` = perlu geocode ulang, `0` = sudah valid. |

### 3. `tbl_agregat_wilayah` (Tabel Pre-computed Dashboard)
| Kolom | Tipe | Keterangan |
|---|---|---|
| `kode_bps` | `VARCHAR(4)` (FK) | Relasi ke `ref_wilayah.kode_bps`. |
| `tahun` | `INTEGER` | Tahun acuan data (contoh: `2024`). |
| `total_rs` | `INTEGER` | Total unit rumah sakit di kabupaten/kota tersebut. |
| `total_tt` | `INTEGER` | Total kapasitas tempat tidur di wilayah tersebut. |
| `jumlah_penduduk` | `INTEGER` | Populasi penduduk acuan. |
| `rasio_tt_per_1000` | `FLOAT` | Rasio tempat tidur per 1.000 penduduk. |
| `kategori_ketercukupan` | `VARCHAR(20)` | Klasifikasi WHO: `hijau` ($\ge 1.0$), `kuning` ($0.7 - 0.99$), `merah` ($< 0.7$). |

### 4. `tbl_indikator_kesehatan` (Tabel Indikator Tematik CSV)
| Kolom | Tipe | Keterangan |
|---|---|---|
| `kode_bps` | `VARCHAR(4)` (FK) | Relasi ke `ref_wilayah.kode_bps`. |
| `tahun` | `INTEGER` | Tahun indikator. |
| `topik` | `VARCHAR(100)` | Kategori data (`Puskesmas`, `Tenaga Medis`, dll). |
| `nama_indikator` | `VARCHAR(255)` | Nama metrik (`Jumlah Puskesmas Rawat Inap`, `Jumlah Dokter Umum`). |
| `nilai` | `FLOAT` | Nilai data numerik. |
| `satuan` | `VARCHAR(50)` | Satuan ukur (`Unit`, `Orang`, `Persen`). |

### 5. `tbl_pipeline_log` (Tabel Audit Trail Pipeline)
| Kolom | Tipe | Keterangan |
|---|---|---|
| `source_id` | `VARCHAR(50)` | Identifier sumber data. |
| `run_started_at` | `TIMESTAMP` | Waktu mulai proses ETL. |
| `run_finished_at` | `TIMESTAMP` | Waktu selesai proses ETL. |
| `record_extracted` | `INTEGER` | Jumlah record yang ditarik dari sumber. |
| `record_loaded` | `INTEGER` | Jumlah record yang berhasil di-upsert ke database. |
| `status` | `enum_pipeline_status`| Status: `SUCCESS`, `PARTIAL`, atau `FAILED`. |
| `error_message` | `TEXT` | Pesan stacktrace jika terjadi error. |

---

## 6. Panduan Konsumsi Data Antar-Jobdesk

### Jobdesk Backend (FastAPI / REST API)
* **Koneksi Database**:
  ```python
  DATABASE_URL = "postgresql+asyncpg://cura_user:cura_password@localhost:5433/cura_db"
  ```
* **Endpoint Rekomendasi**:
  1. `GET /api/v1/hospitals`: Query dari `tbl_rumah_sakit` (filter: `kelas`, `kepemilikan`, `kode_bps`).
  2. `GET /api/v1/hospitals/nearby?lat={lat}&lng={lng}&radius_km=10`: Gunakan fungsi spasial PostGIS:
     ```sql
     SELECT nama_rs, kelas, alamat, telepon, lat, lng,
            ROUND((ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000)::numeric, 2) AS jarak_km
     FROM tbl_rumah_sakit
     WHERE geom IS NOT NULL 
       AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_meters)
     ORDER BY jarak_km ASC;
     ```
  3. `GET /api/v1/wilayah/summary`: Query langsung dari `tbl_agregat_wilayah` untuk respon instan tanpa kalkulasi agregasi berulang.

---

### Jobdesk Frontend (Leaflet / ECharts)
* **Point Markers (Peta RS)**:
  * Konsumsi data RS dari API backend atau file `database/exports/hospitals_clean.csv`.
  * Hanya render marker jika `is_valid_coord === true` (atau `lat !== null && lng !== null`).
* **Peta Choropleth (Batas Wilayah)**:
  * Load file GeoJSON statis: `database/seeds/jatim_districts.geojson`.
  * Cocokkan `feature.properties.KODE_BPS` dengan data `tbl_agregat_wilayah`.
  * Terapkan palet warna standar WHO:
   * `hijau` $\to$ `#2ECC71` (Rasio $\ge 1.0$)
   * `kuning` $\to$ `#F1C40F` (Rasio $0.7 - 0.99$)
   * `merah` $\to$ `#E74C3C` (Rasio $< 0.7$)
  * **Bounding Box Diperluas (v3.0)**: Lat `[-8.8, -5.7]`, Lng `[110.9, 116.6]`. Mencakup Pulau Bawean dan Kepulauan Kangean.
  * **Flag Koordinat**:
  * Hanya render marker jika `is_valid_coord == 1`.
  * RS dengan `needs_geocoding == 1` memerlukan geocode ulang (koordinat dummy/null dari SIRS).

---

### Jobdesk Analis / Riset (Sandbox)
* Gunakan direktori sandbox yang terisolasi agar tidak mengganggu pipeline produksi:
  * `experiments/notebooks/`: Simpan file Jupyter Notebook (.ipynb) untuk EDA, visualisasi Seaborn/Plotly, atau spatial clustering (e.g. `01_data_cleaning_audit.ipynb`, `02_spatial_distribution.ipynb`, `03_bed_capacity_analysis.ipynb`).
  * `experiments/data/`: Tempat menyimpan file dataset sementara.
  * `experiments/scripts/`: Script eksperimen transformasi data ad-hoc.
* Dataset bersih siap analisis tanpa setup database:
  1. `database/exports/hospitals_clean.csv` (447 RS Jawa Timur terstandarisasi).
  2. `database/exports/bed_ratio_38_kab.csv` (Rasio tempat tidur 38 Kab/Kota).
  3. `database/exports/indicators_jatim.csv` (Indikator Puskesmas & Tenaga Medis Dinkes Jatim).

---

### Jobdesk Proposal & PPT
* **Metrik Utama untuk Disitasi**:
  * **Total Faskes**: 447 Rumah Sakit di 38 Kabupaten/Kota Jawa Timur.
  * **Komposisi Kelas RS**: Kelas A (9 RS), Kelas B (68 RS), Kelas C (201 RS), Kelas D (168 RS), Non-Kelas (1 RS).
  * **Komposisi Kepemilikan**: Swasta (259 RS), Pemerintah Daerah/Pusat (149 RS), TNI/Polri (39 RS).
  * **Total Kapasitas Rawat Inap**: 62.391 Tempat Tidur.
  * **Status Ketercukupan Wilayah**: 24 Kab/Kota Ideal (Hijau), 12 Kab/Kota Waspada (Kuning), 2 Kab/Kota Defisit (Merah).
  * **Kab/Kota Rasio Tertinggi**: Kota Malang (4.77) dan Kota Surabaya (4.22 bed per 1.000 penduduk).
  * **Kab/Kota Butuh Intervensi**: Kabupaten Pacitan (0.61 bed per 1.000 penduduk).

---

## 7. Debugging & Pengujian Kualitas Data

Eksekusi rangkaian pengujian kualitas data dengan command berikut:

```bash
# Menjalankan 13 test case terverifikasi (100% PASS)
PYTHONPATH=database pytest database/tests/ -v
```

Cakupan pengujian:
1. `test_sanitize_coordinates_dummy`: Titik dummy Kemenkes dinetralkan ke `null` + `needs_geocoding=1`.
2. `test_sanitize_coordinates_swapped`: Koordinat terbalik otomatis di-swap.
3. `test_sanitize_coordinates_out_of_bounds_jakarta`: Koordinat di luar Jatim ditolak.
4. `test_sanitize_coordinates_bawean_valid`: Pulau Bawean lolos expanded bounding box v3.0.
5. `test_sanitize_coordinates_kangean_valid`: Kepulauan Kangean lolos expanded bounding box v3.0.
6. `test_expanded_bounding_box_constants`: Konstanta bbox sesuai spek v3.0 (lat: -5.7, lng: 116.6).
7. `test_normalize_text_clean`: Whitespace, tab, newline hilang dari alamat.
8. `test_normalize_telepon_trailing_underscore`: Trailing `_` dibersihkan.
9. `test_normalize_telepon_double_space`: Double space di-collapse.
10. `test_normalize_telepon_masking_preserved`: Masking `****` dari sumber SIRS dipertahankan.
11. `test_normalize_telepon_trailing_dash`: Trailing `--` dibersihkan.
12. `test_normalize_nama_rs_trailing_space`: 34 nama RS trailing space di-trim.
13. `test_normalize_kepemilikan_pemerintah`: 6 kategori (Pemkab/Pemkot/Pemprop/Kemkes/Kementerian Lain/BUMN) -> `pemerintah`.
14. `test_normalize_kepemilikan_swasta`: 7 kategori (SWASTA/Perusahaan/Perorangan/Organisasi Islam/Katholik/Protestan/Sosial) -> `swasta`.
15. `test_normalize_kepemilikan_tni_polri`: 4 kategori (TNI AD/AL/AU/POLRI) -> `tni_polri`.
16. `test_quality_gate_v3_pipeline`: End-to-end pipeline (dummy/swapped/Bawean valid/Jakarta null/pemilik_raw audit trail).
17. `test_no_newline_in_cleaned_alamat`: Assert 0 alamat mengandung `\r\n` setelah cleaning.
