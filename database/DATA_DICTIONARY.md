# DATA_DICTIONARY.md — Kamus Data & Panduan Akses Tim (Data Science & Web)
# Proyek: Cura — HealthTrust Facilities Platform
> Versi 2.0 — Panduan Lengkap Retrieval Data dari Clone sampai Siap Pakai

---

## 1. Panduan Cepat Retrieval Data (Dari Clone ke Data Siap Pakai)

### Langkah 1: Clone Repository
```bash
git clone <URL_REPO_HEALTHTRUST>
cd HealthTrust
```

### Langkah 2: Setup Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r database/requirements.txt
```

### Langkah 3: Akses Dataset Bersih Langsung (Zero Database Setup)
Jika hanya butuh data analisis/ML (tidak butuh database SQL):
File sudah tersedia langsung di folder `database/exports/`:
```bash
ls -la database/exports/
```
File siap pakai:
- `hospitals_clean.parquet` & `.csv` (447 RS)
- `bed_ratio_38_kab.parquet` & `.csv` (38 Kab/Kota)
- `indicators_jatim.parquet` & `.csv` (Puskesmas & Nakes)
- `ml_readiness_dataset.parquet` & `.csv` (38 baris × 30 fitur ML siap latih)
- `database/seeds/jatim_districts.geojson` (38 Polygon GeoJSON)

### Langkah 4: Setup Database PostGIS (Khusus Backend / Full-Stack)
Jika butuh SQL & Spatial Queries:
```bash
# 1. Jalankan container PostGIS (Port 5433)
docker-compose up -d

# 2. Inisialisasi tabel dan load data bersih ke PostgreSQL
python3 database/cli.py init-db
python3 database/cli.py seed-all
```

---

## 2. Pemetaan Dataset Berdasarkan Role Tim

| Role Tim | File Dataset yang Dipakai | Alasan / Fitur Target | Format Rekomendasi |
|---|---|---|---|
| **Frontend Developer** | `database/exports/hospitals_clean.csv`<br>`database/exports/bed_ratio_38_kab.csv`<br>`database/seeds/jatim_districts.geojson` | - Katalog faskes (search, filter kelas/jenis RS)<br>- Peta Choropleth Leaflet.js (rasio bed WHO)<br>- Profil statistik ringkasan per Kab/Kota | JSON / GeoJSON / CSV / REST API (`/api/v1/*`) |
| **Machine Learning Engineer** | `database/exports/ml_readiness_dataset.parquet`<br>`database/exports/hospitals_clean.parquet`<br>`database/exports/bed_ratio_38_kab.parquet` | - Multi-factor risk clustering (K-Means/DBSCAN)<br>- Bed demand forecasting (XGBoost/Prophet)<br>- Maternal risk scoring (Random Forest/SHAP)<br>- Spatial facility placement | Parquet (`pd.read_parquet`) |
| **Backend Developer** | Seluruh tabel PostGIS via SQLAlchemy ORM<br>`database/seeds/ref_wilayah_jatim.csv` | - Menyediakan REST API `/api/v1/faskes`, `/api/v1/wilayah/choropleth`, `/api/v1/nakes`, `/api/v1/ask` | SQL Database (`cura_db` port 5433) |

---

## 3. Kamus Data Rinci per Dataset

### 3.1 `hospitals_clean.parquet` / `.csv` (Faskes Rumah Sakit)
- **Primary Key**: `kode_rs` (VARCHAR, 7 digit unik Kemenkes).
- **Baris**: 447 RS se-Jawa Timur.

| Nama Kolom | Tipe Data | Nullable | Deskripsi & Nilai Valid |
|---|---|---|---|
| `kode_rs` | VARCHAR(50) | NO | Kode unik RS resmi Kemenkes (contoh: '3578016'). |
| `nama_rs` | VARCHAR(300) | NO | Nama resmi faskes (trailing whitespace cleaned). |
| `alamat` | TEXT | YES | Alamat lengkap (bebas dari newline `\r\n`). |
| `telepon` | VARCHAR(100) | YES | Nomor kontak faskes (sanitasi trailing underscore). |
| `kode_bps` | CHAR(4) | NO | FK ke `ref_wilayah` (3501–3579). |
| `kelas` | ENUM | NO | Kelas RS: `'A'`, `'B'`, `'C'`, `'D'`. |
| `kepemilikan` | ENUM | NO | Kelompok pemilik: `'pemerintah'`, `'swasta'`, `'tni_polri'`. |
| `pemilik_raw` | VARCHAR(100) | YES | Entitas pemilik asli dari SIRS Kemenkes. |
| `jenis_rs` | VARCHAR(50) | YES | Jenis layanan: `'RSU'`, `'RSIA'`, `'RSK Jiwa'`, dll. |
| `lat` | FLOAT | YES | Latitude koordinat (NULL jika data kotor/dummy). |
| `lng` | FLOAT | YES | Longitude koordinat (NULL jika data kotor/dummy). |
| `is_valid_coord` | INTEGER | NO | `1` jika koordinat valid di Jatim, `0` jika dummy/null. |
| `needs_geocoding` | INTEGER | NO | `1` jika butuh geocoding ulang alamat, `0` jika sudah valid. |
| `sumber_data` | VARCHAR(50) | NO | Asal data: `'sirs_kemenkes'`. |
| `coverage_periode`| VARCHAR(20) | NO | Label masa berlaku data: `'2026-LIVE'`. |

---

### 3.2 `bed_ratio_38_kab.parquet` / `.csv` (Kapasitas Bed & Standar WHO)
- **Primary Key**: `kode_bps` (CHAR 4).
- **Baris**: 38 Kab/Kota.

| Nama Kolom | Tipe Data | Nullable | Deskripsi |
|---|---|---|---|
| `kode_bps` | CHAR(4) | NO | Kode BPS Jawa Timur (3501–3579). |
| `nama_wilayah` | VARCHAR(100) | NO | Nama Kabupaten/Kota. |
| `total_tt` | INTEGER | NO | Total kapasitas tempat tidur rumah sakit di wilayah. |
| `jumlah_penduduk_2021` | INTEGER | NO | Populasi basis sensus/Disdukcapil Kemenkes 2021. |
| `rasio_tt_resmi` | FLOAT | NO | Rasio TT per 1.000 penduduk versi Kemenkes. |
| `kategori_who_resmi` | ENUM | NO | `'hijau'` ($\ge 1.0$), `'kuning'` ($0.7-0.99$), `'merah'` ($< 0.7$). |
| `proyeksi_penduduk_2026` | INTEGER | NO | Estimasi penduduk 2026 (pertumbuhan BPS 0,7%/tahun). |
| `rasio_tt_proyeksi_2026` | FLOAT | NO | Rasio TT aktual dengan pembagi populasi 2026. |
| `kategori_who_proyeksi_2026` | ENUM | NO | Status WHO berbasis rasio proyeksi 2026. |
| `coverage_periode` | VARCHAR(20) | NO | `'2026-PROJECTION'`. |

---

### 3.3 `indicators_jatim.parquet` / `.csv` (Puskesmas & Nakes)
- **Baris**: 114 baris data agregat kesehatan wilayah.

| Nama Kolom | Tipe Data | Nullable | Deskripsi |
|---|---|---|---|
| `kode_bps` | CHAR(4) | NO | Kode BPS Kabupaten/Kota. |
| `nama_wilayah` | VARCHAR(100) | NO | Nama Kabupaten/Kota. |
| `tahun` | INTEGER | NO | Tahun publikasi data (`2024`). |
| `topik` | VARCHAR(50) | NO | Topik data: `'puskesmas'`, `'tenaga_kesehatan'`. |
| `nama_indikator` | VARCHAR(150) | NO | Detail indikator (misal: 'Puskesmas Rawat Inap', 'Dokter'). |
| `nilai` | FLOAT | NO | Nilai angka indikator. |
| `satuan` | VARCHAR(50) | NO | Satuan ukur: `'Unit'`, `'Orang'`. |
| `sumber_data` | VARCHAR(50) | NO | Sumber resmi: `'opendata_jatim'`. |
| `coverage_periode`| VARCHAR(20) | NO | `'2024-OFFICIAL'`. |

---

### 3.4 `ml_readiness_dataset.parquet` (Feature Store untuk ML Engineer)
- **Baris**: 38 baris (1 baris mewakili 1 Kabupaten/Kota).
- **Total Fitur**: 30 fitur numerik siap latih (0 missing values / nulls).
- **Isi Fitur**:
  - Kapasitas: `total_rs`, `total_bed`, `bed_per_1000_2026`, `rasio_who_code`.
  - Faskes Primer: `puskesmas_rawat_inap`, `puskesmas_non_rawat_inap`, `total_puskesmas`.
  - Tenaga Medis: `total_dokter`, `total_perawat`, `total_bidan`, `dokter_per_10k_pop`, `nakes_per_bed`.
  - Morbiditas: Tren kasus rawat inap 10 penyakit, kasus menular (TB, DBD, Diare), kasus PTM (Hipertensi, Diabetes).
  - Outcome KIA: Angka Kematian Ibu (AKI), Angka Kematian Bayi (AKB), Prevalensi Stunting.

---

## 4. Contoh Script Akses Data (Code Snippet)

### Untuk Tim Machine Learning (Python / Pandas / Jupyter)
```python
import pandas as pd

# Load dataset siap latih ML (38 Kab/Kota x 30 Fitur)
df_ml = pd.read_parquet("database/exports/ml_readiness_dataset.parquet")
print("ML Dataset Shape:", df_ml.shape)
print(df_ml.head())

# Fitur untuk clustering risiko kesehatan
X = df_ml[["bed_per_1000_2026", "dokter_per_10k_pop", "total_puskesmas", "aki_per_100k", "stunting_rate"]]
```

### Untuk Tim Frontend (JavaScript / Fetch API atau File Lokal)
```javascript
// Membaca file CSV langsung untuk visualisasi ECharts / Leaflet
async function loadHospitalData() {
  const response = await fetch('/database/exports/hospitals_clean.csv');
  const csvText = await response.text();
  // Parse CSV text menggunakan PapaParse / d3.csvParse
}

// Atau konsumsi langsung dari Backend REST API
async function loadChoroplethData() {
  const response = await fetch('http://localhost:8000/api/v1/wilayah/choropleth');
  const geojson = await response.json();
  // Render ke Leaflet L.geoJSON(geojson).addTo(map);
}
```
