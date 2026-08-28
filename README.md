# Cura — HealthTrust Facilities (Jawa Timur)

Platform analitik dan keterbukaan data geospasial fasilitas kesehatan di Provinsi Jawa Timur. Proyek ini menggabungkan data real-time fasilitas kesehatan (SIRS Kemenkes), indikator kesehatan tematik (Open Data Jatim), serta batas wilayah 38 Kabupaten/Kota (GeoJSON PostGIS) untuk evaluasi rasio ketercukupan layanan kesehatan berbasis standar WHO.

---

## 📌 Panduan Tim Berdasarkan Jobdesk

### 1. ⚙️ Backend Team (FastAPI / REST API)
* **Koneksi Database (PostgreSQL + PostGIS)**:
  * Host: `localhost` | Port: `5433` (Container Docker: `healthtrust_postgis`)
  * Database: `cura_db` | User: `cura_user` | Password: `cura_password`
  * Dialect SQLAlchemy: `postgresql+asyncpg://cura_user:cura_password@localhost:5433/cura_db`
* **Tabel Utama Siap Konsumsi**:
  * `tbl_rumah_sakit`: 447 RS Jawa Timur (nama, kelas A/B/C/D, kepemilikan, alamat, nomor telepon, kolom geometri `geom` SRID 4326).
  * `tbl_agregat_wilayah`: Pre-computed statistics 38 Kab/Kota (total RS, total tempat tidur, populasi, rasio TT/1.000 penduduk, kategori WHO: `hijau`/`kuning`/`merah`). Endpoint peta choropleth bisa query langsung tanpa grouping berat.
  * `tbl_indikator_kesehatan`: 114 record indikator tematik (Puskesmas rawat inap/non rawat inap, jumlah dokter umum).
  * `ref_wilayah`: 38 Kab/Kota Jawa Timur lengkap dengan batas polygon `geom`.
* **Spatial Query Radius / Nearest Hospital**:
  * Kolom `geom` sudah terindeks `GIST` (`idx_tbl_rs_geom`). Query ST_DWithin & ST_Distance berjalan sub-10ms.

---

### 2. 🎨 Frontend Team (Vanilla JS / Leaflet / ECharts)
* **Peta Sebaran Faskes (Point Markers)**:
  * Gunakan kolom `lat` dan `lng` dari `tbl_rumah_sakit` (atau file export `database/exports/hospitals_clean.csv`).
  * Koordinat anomali (dummy laut Bangka Belitung) telah dinetralkan menjadi `null` dengan flag `is_valid_coord = false`.
* **Peta Choropleth Wilayah (Polygon Boundaries)**:
  * File GeoJSON 38 Kab/Kota tersedia di: `database/seeds/jatim_districts.geojson`.
  * Hubungkan `properties.KODE_BPS` dengan field `kode_bps` pada tabel `tbl_agregat_wilayah`.
  * Pewarnaan standar WHO:
    * 🟢 **Hijau (`kategori_ketercukupan: hijau`)**: Rasio $\ge 1.0$ tempat tidur per 1.000 penduduk (Ideal).
    * 🟡 **Kuning (`kategori_ketercukupan: kuning`)**: Rasio $0.7 - 0.99$ (Waspada).
    * 🔴 **Merah (`kategori_ketercukupan: merah`)**: Rasio $< 0.7$ (Defisit).
* **Visualisasi Database GUI**:
  * Akses Adminer via browser di `http://localhost:8080` (System: `PostgreSQL`, Server: `postgres`, User: `cura_user`, Pass: `cura_password`, DB: `cura_db`).

---

### 3. 📊 Tim Proposal, PPT & Analis Data
* **Data Siap Pakai (No DB Setup Required)**:
  * File CSV bersih dapat langsung diambil dari: `database/exports/hospitals_clean.csv`.
  * Workspace Sandbox untuk eksperimen/EDA: `experiments/notebooks/` dan `experiments/data/`.
* **Fakta & Angka Kunci Jawa Timur (Insight untuk Presentasi / Proposal)**:
  * **Total Rumah Sakit**: 447 RS aktif (368 RSU, 59 RSIA, 5 RSK Mata, 5 RSK Gigi/Mulut, 4 RSK Bedah, 2 RSK Paru, 2 RSK Jiwa, 1 RSK Kanker, 1 RS Bergerak).
  * **Total Kapasitas Tempat Tidur**: 62.391 Bed.
  * **Status Ketercukupan Wilayah**: 24 Kab/Kota Kategori Hijau (Ideal), 12 Kab/Kota Kategori Kuning (Waspada), 2 Kab/Kota Kategori Merah (Defisit).
  * **Rasio Tertinggi**: Kota Malang (4.77) dan Kota Surabaya (4.22 bed/1.000 penduduk).
  * **Daerah Butuh Perhatian**: Kabupaten Pacitan (0.61 bed/1.000 penduduk).

---

## 🚀 Quickstart & Setup Developer

### 1. Menjalankan Layanan Docker (Database & Adminer)
```bash
# Menyalakan PostGIS (port 5433) dan Adminer (port 8080)
docker-compose up -d

# Cek status container
docker-compose ps
```

### 2. Setup Virtual Environment & CLI
```bash
# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r database/requirements.txt

# Menjalankan Health Check Endpoint & DB
PYTHONPATH=database python database/cli.py check-health

# Inisialisasi Skema & Indeks PostGIS
PYTHONPATH=database python database/cli.py init-db

# Menjalankan Full ETL Pipeline (Live Fetch -> Clean -> Upsert -> Export CSV)
PYTHONPATH=database python database/cli.py run-etl

# Menjalankan Test Suite Kualitas Data
PYTHONPATH=database python database/cli.py test-db
```

### 3. Menjalankan Scheduler Otomatis
```bash
# Default: Update data tiap Senin jam 07:00 WIB
PYTHONPATH=database python database/cli.py scheduler

# Opsi harian:
PYTHONPATH=database python database/cli.py scheduler --day daily --hour 7 --minute 0
```

---

## 📁 Struktur Proyek

```text
HealthTrust/
├── database/
│   ├── config/              # Konfigurasi koneksi & registry data sources
│   ├── exports/             # Export CSV bersih siap konsumsi (hospitals_clean.csv)
│   ├── health/              # Health check checker API eksternal & DB
│   ├── pipeline/            # ETL pipeline (fetcher, cleaner, loader, orchestrator, crawler)
│   ├── raw/                 # Snapshot immutable data mentah (git-ignored)
│   ├── seeds/               # Data referensi statis (wilayah & GeoJSON Jatim)
│   ├── tests/               # Test suite & quality gates
│   ├── cli.py               # CLI master runner
│   ├── models.py            # Model tabel SQLAlchemy & PostGIS
│   └── scheduler.py         # Scheduler daemon otomatis
│
├── experiments/             # Sandbox data analis (notebooks, scripts, data)
├── backend/                 # API Service FastAPI (konsumsi data PostGIS)
├── frontend/                # Web Dashboard Leaflet & ECharts
├── docker-compose.yml       # Definisi container PostGIS & Adminer
└── README.md                # Dokumentasi utama proyek
```
