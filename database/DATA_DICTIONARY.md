# Data Dictionary & Developer Guide — Cura (HealthTrust Facilities)
> Dokumentasi teknis terstandarisasi untuk konsumsi dataset, kamus data (schema), relasi tabel, dan contoh query/resep analisis data bagi tim Backend, Machine Learning / Analis Data, dan Frontend.

---

## 📑 Daftar Isi
1. [Inventaris Dataset Siap Pakai (`database/exports/`)](#1-inventaris-dataset-siap-pakai-databaseexports)
2. [Kamus Data & Skema Kolom (Data Dictionary)](#2-kamus-data--skema-kolom-data-dictionary)
   - [A. Dataset Rumah Sakit (`hospitals_clean`)](#a-dataset-rumah-sakit-hospitals_clean)
   - [B. Dataset Rasio Tempat Tidur Wilayah (`bed_ratio_38_kab`)](#b-dataset-rasio-tempat-tidur-wilayah-bed_ratio_38_kab)
   - [C. Dataset Indikator Tematik Kesehatan (`indicators_jatim`)](#c-dataset-indikator-tematik-kesehatan-indicators_jatim)
   - [D. Batas Wilayah Spasial GIS (`jatim_districts.geojson`)](#d-batas-wilayah-spasial-gis-jatim_districtsgeojson)
3. [Relasi Entitas & Kunci Penghubung (Data Relationships)](#3-relasi-entitas--kunci-penghubung-data-relationships)
4. [Resep Analisis Siap Pakai (Data Recipes for Python / Pandas / DuckDB)](#4-resep-analisis-siap-pakai-data-recipes-for-python--pandas--duckdb)
5. [Panduan Integrasi Backend & PostGIS Spatial View](#5-panduan-integrasi-backend--postgis-spatial-view)
6. [Panduan Visualisasi Frontend (Leaflet & ECharts)](#6-panduan-visualisasi-frontend-leaflet--echarts)

---

## 1. Inventaris Dataset Siap Pakai (`database/exports/`)

Semua dataset di bawah ini dihasilkan secara otomatis oleh pipeline ETL terverifikasi (28 Quality Gate Tests). Tersedia dalam format ganda: **`.parquet`** (direkomendasikan untuk Python/ML: tipe data presisi & loading instan) dan **`.csv`** (untuk inspeksi cepat).

| Dataset | File Path | Baris × Kolom | Sumber Data | Status Kelayakan |
|---|---|---|---|---|
| **Data RS Bersih** | `database/exports/hospitals_clean.parquet`<br>`database/exports/hospitals_clean.csv` | 447 baris × 17 kolom | SIRS Kemenkes (List + Rekap + OSM Geocoder) | ✅ Siap Pakai. 420 koordinat valid, 27 disanitasi jadi `null`. |
| **Rasio TT 38 Kab/Kota** | `database/exports/bed_ratio_38_kab.parquet`<br>`database/exports/bed_ratio_38_kab.csv` | 38 baris × 6 kolom | SIRS Kemenkes & Disdukcapil | ✅ Siap Pakai. Tanpa nilai null, mencakup rasio WHO. |
| **Indikator Tematik** | `database/exports/indicators_jatim.parquet`<br>`database/exports/indicators_jatim.csv` | 114 baris × 7 kolom | Open Data Jatim & Dinkes Jatim 2024 | ✅ Siap Pakai. Puskesmas Inap/Non-inap & Dokter Umum. |
| **Polygon Wilayah GIS** | `database/seeds/jatim_districts.geojson` | 38 Features (MultiPolygon) | SIRS & BPS Jawa Timur (WGS84) | ✅ Siap Pakai untuk Layer Choropleth Peta. |

---

## 2. Kamus Data & Skema Kolom (Data Dictionary)

### A. Dataset Rumah Sakit (`hospitals_clean`)
Tabel master faskes rumah sakit di seluruh 38 Kabupaten/Kota Jawa Timur.

| Nama Kolom | Tipe Data | Nullable? | Nilai / Enum / Format | Deskripsi |
|---|---|---|---|---|
| `kode_rs` | `VARCHAR(20)` | ❌ Tidak (PK) | Contoh: `'3578016'` | 7-digit ID unik Rumah Sakit terdaftar di Kemenkes RI. |
| `nama_rs` | `VARCHAR(150)` | ❌ Tidak | String (Trimmed) | Nama resmi faskes (contoh: `'RS Umum Daerah Dr. Soetomo'`). |
| `alamat` | `TEXT` | ⚠️ Ya | String (Sanitized) | Alamat fisik faskes, bebas dari karakter escape `\r\n` dan spasi berlebih. |
| `kode_bps` | `VARCHAR(10)` | ❌ Tidak (FK) | `'3501'` s/d `'3579'` | Kode referensi wilayah BPS 4-digit Jawa Timur. |
| `kelas` | `VARCHAR(10)` | ❌ Tidak | `'A'`, `'B'`, `'C'`, `'D'`, `'tidak_diketahui'` | Klasifikasi tipe pelayanan faskes Kemenkes. |
| `kepemilikan` | `VARCHAR(20)` | ❌ Tidak | `'pemerintah'`, `'swasta'`, `'tni_polri'`, `'lainnya'` | Standardisasi kepemilikan faskes (hasil reduksi 17 kategori mentah). |
| `pemilik_raw` | `VARCHAR(100)` | ⚠️ Ya | Contoh: `'Pemkab'`, `'BUMN'`, `'Organisasi Islam'` | Nilai mentah kategori kepemilikan dari SIRS sebelum mapping (audit trail). |
| `jenis_rs` | `VARCHAR(50)` | ⚠️ Ya | `'RSU'`, `'RSIA'`, `'RSK Jiwa'`, `'RSK Mata'`, dll. | Spesialisasi faskes (Umum vs Rumah Sakit Khusus). |
| `jumlah_tt` | `INTEGER` | ❌ Tidak | $\ge 0$ | Total kapasitas tempat tidur rawat inap faskes aktif. |
| `layanan` | `JSON / TEXT` | ❌ Tidak | Contoh: `'[]'` atau `'["IGD", "ICU"]'` | Daftar layanan medis unggulan faskes (format JSON array). |
| `telepon` | `VARCHAR(50)` | ⚠️ Ya | String (Sanitized) | Kontak telepon resmi faskes (bebas trailing `_` dan spasi ganda). |
| `website` | `VARCHAR(255)` | ⚠️ Ya | URL string / `null` | Alamat portal web resmi faskes. |
| `lat` | `FLOAT` | ⚠️ Ya | `-8.8` s/d `-5.7` atau `null` | Titik koordinat Latitude geografis (WGS84). |
| `lng` | `FLOAT` | ⚠️ Ya | `110.9` s/d `116.6` atau `null` | Titik koordinat Longitude geografis (WGS84). |
| `is_valid_coord`| `INTEGER / BOOL` | ❌ Tidak | `1` (Valid) atau `0` (Tidak) | Flag integritas koordinat (0 jika dummy Bangka Belitung atau out-of-bounds). |
| `needs_geocoding` | `INTEGER / BOOL` | ❌ Tidak | `1` (Perlu) atau `0` (Tidak) | Flag penanda faskes yang koordinatnya null dan perlu geocoding lanjutan. |
| `sumber_data` | `VARCHAR(50)` | ❌ Tidak | `'SIRS Kemenkes'` | Metadata sumber pipeline data. |

---

### B. Dataset Rasio Tempat Tidur Wilayah (`bed_ratio_38_kab`)
Ringkasan agregat rasio ketersediaan tempat tidur rumah sakit per 1.000 penduduk berstandar World Health Organization (WHO).

| Nama Kolom | Tipe Data | Nullable? | Nilai / Contoh | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(10)` | ❌ Tidak (PK) | `'3501'` s/d `'3579'` | Kode BPS 4 digit Kabupaten/Kota. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | Contoh: `'Kabupaten Pacitan'` | Nama wilayah terstandarisasi dengan prefix Kabupaten/Kota. |
| `total_tt` | `INTEGER` | ❌ Tidak | Contoh: `337` | Akumulasi seluruh tempat tidur rumah sakit di wilayah tersebut. |
| `jumlah_penduduk` | `INTEGER` | ❌ Tidak | Contoh: `555984` | Populasi resmi penduduk (Rujukan Disdukcapil). |
| `rasio_tt_per_1000` | `FLOAT` | ❌ Tidak | Contoh: `0.61` | Rumus: $(\text{total\_tt} / \text{jumlah\_penduduk}) \times 1.000$. |
| `kategori_who` | `VARCHAR(20)` | ❌ Tidak | `'hijau'`, `'kuning'`, `'merah'` | Kategori ketercukupan standar WHO:<br>🟢 `hijau`: Rasio $\ge 1.0$ (Ideal)<br>🟡 `kuning`: Rasio $0.7 - 0.99$ (Waspada)<br>🔴 `merah`: Rasio $< 0.7$ (Defisit Kritis) |

---

### C. Dataset Indikator Tematik Kesehatan (`indicators_jatim`)
Data indikator makro fasilitas tingkat pertama (FKTP) dan tenaga medis dari Open Data Jawa Timur.

| Nama Kolom | Tipe Data | Nullable? | Nilai / Contoh | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(10)` | ❌ Tidak (FK) | `'3501'` s/d `'3579'` | Kode BPS wilayah Jawa Timur. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | Contoh: `'Kabupaten Malang'` | Nama Kabupaten/Kota rujukan. |
| `tahun` | `INTEGER` | ❌ Tidak | `2024` | Tahun rujukan data indikator. |
| `nama_indikator` | `VARCHAR(100)` | ❌ Tidak | `'puskesmas_rawat_inap'`, `'puskesmas_non_rawat_inap'`, `'dokter_umum'` | Variabel indikator kesehatan yang dicatat. |
| `nilai` | `FLOAT` | ❌ Tidak | Contoh: `39.0` | Nilai kuantitatif indikator. |
| `satuan` | `VARCHAR(50)` | ❌ Tidak | `'Unit'`, `'Orang'` | Satuan pengukuran metrik. |
| `sumber_data` | `VARCHAR(100)` | ❌ Tidak | `'Dinas Kesehatan Provinsi Jawa Timur'` | Sumber data resmi pemerintah provinsi. |

---

### D. Batas Wilayah Spasial GIS (`jatim_districts.geojson`)
Objek FeatureCollection GeoJSON untuk 38 batas administratif Kabupaten/Kota Jawa Timur (termasuk Pulau Madura, Pulau Bawean, dan Kepulauan Kangean).
* **Format**: Standard GeoJSON FeatureCollection (CRS: `EPSG:4326` / WGS84).
* **Properties per Feature**:
  * `KODE_BPS` / `ID2013`: String kode 4-digit (misal: `"3578"`).
  * `PROVINSI`: Nama wilayah (misal: `"Kota Surabaya"`).
  * `jumlah_penduduk`: Integer populasi dasar.

---

## 3. Relasi Entitas & Kunci Penghubung (Data Relationships)

Seluruh dataset dirancang dengan arsitektur relasional yang rapi menggunakan **`kode_bps`** sebagai *Primary / Foreign Key universal*:

```text
┌────────────────────────────────────────────────────────┐
│               ref_wilayah / GeoJSON                    │
│   (kode_bps PK: '3501' - '3579', nama_wilayah, geom)   │
└───────────┬────────────────────────────────┬───────────┘
            │ 1:N                            │ 1:1
            ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│       hospitals_clean        │ │      bed_ratio_38_kab        │
│ (kode_rs PK, kode_bps FK,    │ │ (kode_bps PK/FK, total_tt,   │
│  kelas, kepemilikan, geom)   │ │  rasio_tt_per_1000, kategori)│
└──────────────────────────────┘ └──────────────────────────────┘
            │
            │ 1:N
            ▼
┌──────────────────────────────┐
│       indicators_jatim       │
│ (kode_bps FK, tahun,         │
│  nama_indikator, nilai)      │
└──────────────────────────────┘
```

---

## 4. Resep Analisis Siap Pakai (Data Recipes for Python / Pandas / DuckDB)

### Resep 1: Load Dataset Cepat dengan Pandas (Parquet)
```python
import pandas as pd

# Load dataset utama
df_rs = pd.read_parquet("database/exports/hospitals_clean.parquet")
df_ratio = pd.read_parquet("database/exports/bed_ratio_38_kab.parquet")
df_ind = pd.read_parquet("database/exports/indicators_jatim.parquet")

print(f"Total RS: {len(df_rs)} | Total Wilayah: {len(df_ratio)}")
```

### Resep 2: Filter RS Valid untuk Visualisasi Titik Peta (GIS)
```python
# Selalu filter is_valid_coord == 1 agar titik tidak lari ke luar Jawa Timur
df_gis = df_rs[df_rs["is_valid_coord"] == 1]
print(f"RS siap plotting peta: {len(df_gis)} faskes")
```

### Resep 3: Analisis Wilayah Kritis Tempat Tidur (Standar WHO < 1.0)
```python
# Ambil daerah dengan rasio TT di bawah standar WHO (< 1.0 per 1.000 penduduk)
df_defisit = df_ratio[df_ratio["kategori_who"].isin(["merah", "kuning"])].sort_values(
    by="rasio_tt_per_1000", ascending=True
)
print(df_defisit[["nama_wilayah", "total_tt", "jumlah_penduduk", "rasio_tt_per_1000", "kategori_who"]])
```

### Resep 4: Pivot Table Distribusi Kelas RS per Kepemilikan
```python
pivot_rs = pd.crosstab(
    df_rs["kepemilikan"], 
    df_rs["kelas"], 
    margins=True, 
    margins_name="Total"
)
print(pivot_rs)
```

### Resep 5: Query Cepat SQL In-Memory Menggunakan DuckDB
```python
import duckdb

con = duckdb.connect()
query = """
SELECT 
    r.nama_wilayah,
    r.kategori_who,
    r.rasio_tt_per_1000,
    COUNT(h.kode_rs) AS jumlah_rs,
    SUM(h.jumlah_tt) AS kapasitas_tt
FROM 'database/exports/bed_ratio_38_kab.parquet' r
LEFT JOIN 'database/exports/hospitals_clean.parquet' h ON r.kode_bps = h.kode_bps
GROUP BY r.nama_wilayah, r.kategori_who, r.rasio_tt_per_1000
ORDER BY r.rasio_tt_per_1000 ASC
LIMIT 10;
"""
print(con.execute(query).df())
```

---

## 5. Panduan Integrasi Backend & PostGIS Spatial View

Bagi tim backend yang menggunakan FastAPI + SQLAlchemy / PostGIS:

### A. Koneksi Database Container
```python
DATABASE_URL = "postgresql+asyncpg://cura_user:cura_password@localhost:5433/cura_db"
```

### B. Query View Siap Saji (`v_choropleth_wilayah`)
Tidak perlu melakukan multiple JOIN manual. Gunakan view bawaan database:
```sql
SELECT 
    kode_bps, 
    nama_wilayah, 
    tipe, 
    total_rs, 
    total_tt, 
    jumlah_penduduk, 
    rasio_tt_per_1000, 
    kategori_ketercukupan, 
    ST_AsGeoJSON(geom) AS geojson
FROM v_choropleth_wilayah;
```

### C. Query Spasial Pencarian RS Terdekat (Radius Filter)
```sql
SELECT 
    kode_rs, 
    nama_rs, 
    kelas, 
    kepemilikan, 
    alamat, 
    telepon, 
    lat, 
    lng,
    ROUND((ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000)::numeric, 2) AS jarak_km
FROM tbl_rumah_sakit
WHERE is_valid_coord = 1
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_meters)
ORDER BY jarak_km ASC;
```

---

## 6. Panduan Visualisasi Frontend (Leaflet & ECharts)

### A. Peta Choropleth Wilayah (Leaflet.js)
1. Muat polygon dari `database/seeds/jatim_districts.geojson` atau view API backend.
2. Terapkan palet warna standar WHO:
   * 🟢 **Hijau (`kategori_who == 'hijau'`)**: `#2ECC71` (Rasio $\ge 1.0$)
   * 🟡 **Kuning (`kategori_who == 'kuning'`)**: `#F1C40F` (Rasio $0.7 - 0.99$)
   * 🔴 **Merah (`kategori_who == 'merah'`)**: `#E74C3C` (Rasio $< 0.7$)

### B. Pin Marker Rumah Sakit (Leaflet Marker Cluster)
1. Gunakan koordinat `lat` dan `lng` dari `hospitals_clean.parquet` (filter `is_valid_coord == 1`).
2. Tentukan warna pin marker berdasarkan `kepemilikan`:
   * **Pemerintah**: Biru (`#3498DB`)
   * **Swasta**: Hijau (`#2ECC71`)
   * **TNI/Polri**: Merah / Oranye (`#E67E22`)
