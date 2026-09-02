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
| `sumber_data` | `VARCHAR(50)` | ❌ Tidak | `'SIRS Kemenkes'` | Metadata institusi sumber pipeline data. |
| `coverage_periode` | `VARCHAR(20)` | ❌ Tidak | `'2026-LIVE'` | Periode rujukan data (Kaidah Data Freshness PRD v1.1). |

---

### B. Dataset Puskesmas Jawa Timur (`puskesmas_clean`)
Tabel master faskes Puskesmas (Pusat Kesehatan Masyarakat) di 38 Kabupaten/Kota Jawa Timur (Domain A - PRD F02).
* **Format File**: `database/exports/puskesmas_clean.csv` dan `puskesmas_clean.parquet`
* **Jumlah Record**: 977 Puskesmas

| Nama Kolom | Tipe Data | Nullable? | Nilai / Format | Deskripsi |
|---|---|---|---|---|
| `kode_puskesmas` | `VARCHAR(50)` | ❌ Tidak (PK) | `'PKM35780001'` | Kode unik pengenal Puskesmas. |
| `nama` | `VARCHAR(300)` | ❌ Tidak | `'Puskesmas Tegalsari Rawat Inap 1'` | Nama resmi faskes Puskesmas. |
| `tipe_rawat` | `VARCHAR(20)` | ❌ Tidak | `'rawat_inap'` / `'non_rawat_inap'` | Klasifikasi tipe perawatan faskes. |
| `alamat` | `TEXT` | ⚠️ Ya | `'Jl. Raya Kesehatan No. 1, Kota Surabaya'` | Alamat faskes bersih dari newline `\r\n`. |
| `kode_bps` | `VARCHAR(4)` | ⚠️ Ya (FK) | `'3578'` | Kode BPS 4 digit Kabupaten/Kota. |
| `kecamatan` | `VARCHAR(100)` | ⚠️ Ya | `'Kecamatan 1'` | Nama kecamatan faskes berada. |
| `telepon` | `VARCHAR(100)` | ⚠️ Ya | `'031-8123456'` | Nomor telepon kontak faskes. |
| `jumlah_tt` | `INTEGER` | ❌ Tidak | `15` (Rawat Inap) / `0` (Non) | Jumlah kapasitas tempat tidur faskes. |
| `lat` | `FLOAT` | ⚠️ Ya | `-7.280000` | Titik koordinat Latitude (WGS84). |
| `lng` | `FLOAT` | ⚠️ Ya | `112.740000` | Titik koordinat Longitude (WGS84). |
| `is_valid_coord` | `INTEGER` | ❌ Tidak | `1` atau `0` | Flag penanda koordinat dalam batas Jatim. |
| `source_id` | `VARCHAR(50)` | ❌ Tidak | `'opendata_jatim'` | Identifier sumber data rujukan. |
| `coverage_periode` | `VARCHAR(20)` | ❌ Tidak | `'2024-OFFICIAL'` | Periode rujukan data resmi Dinkes Jatim. |

---

### C. Dataset Rasio Tempat Tidur Wilayah (`bed_ratio_38_kab`)
Ringkasan agregat rasio ketersediaan tempat tidur rumah sakit per 1.000 penduduk berstandar World Health Organization (WHO).

| Nama Kolom | Tipe Data | Nullable? | Nilai / Contoh | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(10)` | ❌ Tidak (PK) | `'3501'` s/d `'3579'` | Kode BPS 4 digit Kabupaten/Kota. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | Contoh: `'Kabupaten Pacitan'` | Nama wilayah terstandarisasi dengan prefix Kabupaten/Kota. |
| `total_tt` | `INTEGER` | ❌ Tidak | Contoh: `337` | Akumulasi seluruh tempat tidur rumah sakit di wilayah tersebut. |
| `jumlah_penduduk_2021` | `INTEGER` | ❌ Tidak | Contoh: `555984` | Populasi resmi penduduk baseline (Disdukcapil). |
| `rasio_tt_resmi` | `FLOAT` | ❌ Tidak | Contoh: `0.61` | Rasio TT resmi Kemenkes per 1.000 penduduk. |
| `kategori_who_resmi` | `VARCHAR(20)` | ❌ Tidak | `'hijau'`, `'kuning'`, `'merah'` | Kategori ketercukupan resmi baseline. |
| `proyeksi_penduduk_2026` | `INTEGER` | ❌ Tidak | Contoh: `575716` | Proyeksi populasi BPS 2026 (Laju pertumbuhan ~0.7%/tahun). |
| `rasio_tt_proyeksi_2026` | `FLOAT` | ❌ Tidak | Contoh: `0.59` | Rasio TT proyeksi 2026 per 1.000 penduduk. |
| `kategori_who_proyeksi_2026` | `VARCHAR(20)` | ❌ Tidak | `'hijau'`, `'kuning'`, `'merah'` | Kategori ketercukupan standar WHO proyeksi 2026:<br>🟢 `hijau`: Rasio $\ge 1.0$ (Ideal)<br>🟡 `kuning`: Rasio $0.7 - 0.99$ (Waspada)<br>🔴 `merah`: Rasio $< 0.7$ (Defisit Kritis) |
| `coverage_periode` | `VARCHAR(20)` | ❌ Tidak | `'2026-PROJECTED'` | Metadata periode proyeksi data kependudukan. |

---

### D. Dataset Tenaga Kesehatan / SDM Medis (`healthcare_workforce`)
Tabel rincian jumlah tenaga medis (Dokter Umum, Spesialis, Gigi, Perawat, Bidan, Ahli Gizi, Sanitasi) per Kabupaten/Kota (Domain B - PRD F04 & F05).
* **Format File**: `database/exports/healthcare_workforce.csv` dan `healthcare_workforce.parquet`
* **Jumlah Record**: 266 baris (38 Kab/Kota × 7 profesi nakes)

| Nama Kolom | Tipe Data | Nullable? | Nilai / Enum | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(4)` | ❌ Tidak (FK) | `'3501'` s/d `'3579'` | Kode BPS 4 digit Kabupaten/Kota. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | `'Kabupaten Pacitan'` | Nama wilayah terstandarisasi. |
| `tahun` | `INTEGER` | ❌ Tidak | `2024` | Tahun rujukan data dinas. |
| `semester` | `INTEGER` | ❌ Tidak | `1` atau `2` | Semester pelaporan. |
| `jenis_nakes` | `VARCHAR(50)` | ❌ Tidak | `'dokter_umum'`, `'dokter_spesialis'`, `'perawat'`, dll. | Klasifikasi profesi tenaga kesehatan. |
| `jumlah` | `INTEGER` | ❌ Tidak | $\ge 0$ | Total personil nakes bertugas. |
| `faskes_level` | `VARCHAR(50)` | ❌ Tidak | `'Semua Faskes'` | Tingkat penugasan fasilitas. |
| `sumber_data` | `VARCHAR(100)` | ❌ Tidak | `'Dinas Kesehatan Provinsi Jawa Timur'` | Sumber data resmi. |

---

### E. Dataset Morbiditas & Kasus Penyakit (`disease_morbidity_trends`)
Trend kasus 10 penyakit terbanyak rawat inap & jalan per triwulanan di 38 Kab/Kota (Domain C - PRD F06 & Trend Forecasting).
* **Format File**: `database/exports/disease_morbidity_trends.csv` dan `disease_morbidity_trends.parquet`
* **Jumlah Record**: 1.520 baris (38 Kab/Kota × 4 Triwulan × 10 Penyakit)

| Nama Kolom | Tipe Data | Nullable? | Nilai / Contoh | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(4)` | ❌ Tidak (FK) | `'3578'` | Kode BPS Kabupaten/Kota. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | `'Kota Surabaya'` | Nama wilayah pelaporan. |
| `tahun` | `INTEGER` | ❌ Tidak | `2024` | Tahun pelaporan. |
| `triwulan` | `VARCHAR(10)` | ❌ Tidak | `'Q1'`, `'Q2'`, `'Q3'`, `'Q4'` | Kuartal pencatatan epidemiologi. |
| `tipe_pelayanan`| `VARCHAR(20)` | ❌ Tidak | `'rawat_inap'`, `'rawat_jalan'` | Jalur perawatan pasien. |
| `nama_penyakit` | `VARCHAR(200)` | ❌ Tidak | `'Demam Berdarah Dengue (DBD)'` | Nama diagnosis penyakit. |
| `kode_icd10` | `VARCHAR(10)` | ⚠️ Ya | `'A90'`, `'A15'`, `'J06'`, dll. | Kode ICD-10 WHO. |
| `jumlah_pasien` | `INTEGER` | ❌ Tidak | $\ge 0$ | Akumulasi kasus pasien terdaftar. |
| `status_kasus` | `VARCHAR(20)` | ❌ Tidak | `'menular'` / `'tidak_menular'` | Sifat epidemiologi penyakit. |

---

### F. Dataset Siap Latih Machine Learning (`ml_readiness_dataset`)
Dataset terpadu multi-domain (Faskes + SDM Medis + Morbiditas + Demografi) yang diagregasi per Kabupaten/Kota siap latih model Machine Learning.
* **Format File**: `database/exports/ml_readiness_dataset.csv` dan `ml_readiness_dataset.parquet`
* **Dimensi**: 38 baris × 30 fitur (*Engineered Features*)
* **Fitur Utama**:
  * Kapasitas Bed: `total_tt`, `rasio_tt_resmi`, `rasio_tt_proyeksi_2026`, `kategori_who_proyeksi_2026`
  * Jumlah Faskes: `total_rs`, `rs_pemerintah`, `rs_swasta`, `total_puskesmas`, `puskesmas_rawat_inap`, `puskesmas_non_rawat_inap`
  * SDM Nakes: `dokter_umum`, `dokter_spesialis`, `perawat`, `bidan`, `rasio_dokter_per_1000`, `rasio_perawat_per_1000`
  * Beban Morbiditas: `total_kasus_pasien_tahunan`, `kasus_rawat_inap_tahunan`, `kasus_menular_tahunan`

---

### G. Dataset Kesehatan Ibu & Anak (`maternal_child_health`)
Tabel sub-domain KIA per Kabupaten/Kota: AKI, AKB, AKABA, Prevalensi Stunting, Gizi Buruk, K4 Coverage, Imunisasi IDL (PRD F-PP03).
* **Format File**: `database/exports/maternal_child_health.csv` dan `maternal_child_health.parquet`
* **Jumlah Record**: 38 baris (38 Kab/Kota)

| Nama Kolom | Tipe Data | Nullable? | Nilai / Contoh | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(4)` | ❌ Tidak (FK) | `'3578'` | Kode BPS 4 digit. |
| `nama_wilayah` | `VARCHAR(100)` | ❌ Tidak | `'Kota Surabaya'` | Nama wilayah. |
| `tahun` | `INTEGER` | ❌ Tidak | `2024` | Tahun rujukan data. |
| `aki` | `FLOAT` | ⚠️ Ya | `85.4` | Angka Kematian Ibu per 100.000 KH. |
| `akb` | `FLOAT` | ⚠️ Ya | `12.1` | Angka Kematian Bayi per 1.000 KH. |
| `prevalensi_stunting` | `FLOAT` | ⚠️ Ya | `14.2` | Persentase balita stunting (%). |
| `cakupan_idl` | `FLOAT` | ⚠️ Ya | `95.8` | Cakupan Imunisasi Dasar Lengkap (%). |
| `k4_coverage` | `FLOAT` | ⚠️ Ya | `91.0` | Cakupan Kunjungan Antenatal K4 (%). |

---

### H. Dataset Surveilans Penyakit Cepat KLB (`disease_surveillance_weekly`)
Kalkulasi deteksi lonjakan mingguan/bulanan penyakit potensial KLB: DBD, Diare, ISPA, Leptospirosis (PRD F-PP05).
* **Format File**: `database/exports/disease_surveillance_weekly.csv` dan `disease_surveillance_weekly.parquet`
* **Jumlah Record**: 152 baris (38 Kab/Kota × 4 Penyakit)

| Nama Kolom | Tipe Data | Nullable? | Nilai / Enum | Deskripsi |
|---|---|---|---|---|
| `kode_bps` | `VARCHAR(4)` | ❌ Tidak (FK) | `'3515'` | Kode BPS Kabupaten/Kota. |
| `kode_icd10` | `VARCHAR(10)` | ❌ Tidak (FK) | `'A90'` | Kode ICD-10 WHO. |
| `periode_bulan` | `VARCHAR(10)` | ❌ Tidak | `'2026-08'` | Periode evaluasi surveilans. |
| `kasus_bulan_ini` | `INTEGER` | ❌ Tidak | `45` | Jumlah kasus tercatat bulan ini. |
| `rata_rata_3bln` | `FLOAT` | ❌ Tidak | `22.5` | Rata-rata kasus 3 bulan sebelumnya. |
| `delta_persen` | `FLOAT` | ❌ Tidak | `+100.0` | Persentase kenaikan kasus (%). |
| `status_surveillance` | `VARCHAR(20)` | ❌ Tidak | `'normal'`, `'waspada'`, `'perhatian'` | Status deteksi anomali. |

---

### I. Dataset Peringatan Dini Aktif (`active_alerts`)
Daftar insiden peringatan dini yang terpicu secara otomatis oleh Early Warning Rule Engine (PRD F-EW01 & F-EW02).
* **Format File**: `database/exports/active_alerts.csv` dan `active_alerts.parquet`

---

### J. Dataset Indikator Tematik Kesehatan (`indicators_jatim`)
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

### E. Tabel Katalog Referensi (`ref_sumber_data` & `ref_icd10`)

#### 1. `ref_sumber_data` (Katalog Sumber Data Resmi & Legalitas Lisensi)
| Kolom | Tipe Data | Nullable? | Deskripsi |
|---|---|---|---|
| `source_id` | `VARCHAR(50)` | ❌ Tidak (PK) | Unique ID sumber (e.g. `'sirs_kemenkes'`, `'opendata_jatim'`). |
| `nama` | `VARCHAR(200)` | ❌ Tidak | Nama resmi portal/API sumber data. |
| `institusi` | `VARCHAR(200)` | Ya | Lembaga/OPD pengelola data. |
| `url` | `TEXT` | Ya | URL endpoint portal sumber. |
| `lisensi` | `VARCHAR(200)` | Ya | Lisensi data (e.g. UU KIP No.14/2008, MIT, CC-BY). |
| `frekuensi_update` | `VARCHAR(50)` | Ya | Frekuensi update (`daily`, `weekly`, `monthly`, `annual`, `once`). |

#### 2. `ref_icd10` (Master Kode Penyakit Rujukan)
| Kolom | Tipe Data | Nullable? | Deskripsi |
|---|---|---|---|
| `kode` | `VARCHAR(10)` | ❌ Tidak (PK) | Kode ICD-10 resmi (e.g. `'A15'`, `'A90'`, `'E45'`). |
| `nama_en` | `VARCHAR(300)` | Ya | Nama penyakit internasional (WHO). |
| `nama_id` | `VARCHAR(300)` | Ya | Nama penyakit Bahasa Indonesia baku. |
| `kategori` | `VARCHAR(100)` | Ya | Kategori penyakit (Infeksi, Tular Vektor, Gangguan Gizi, dll). |

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

### B. Pre-Built Spatial View: `v_faskes_all` (Marker Layer Peta Leaflet)
Menyatukan seluruh faskes (Rumah Sakit + Puskesmas) dalam satu query instan:
```sql
SELECT 
    id_faskes, 
    jenis_faskes, 
    nama, 
    kelas_tipe, 
    kepemilikan, 
    alamat, 
    telepon, 
    jumlah_tt, 
    lat, 
    lng, 
    ST_AsGeoJSON(geom)::json AS geojson_point
FROM v_faskes_all
WHERE is_valid_coord = 1;
```

### C. Pre-Built Spatial View: `v_choropleth_wilayah` (Choropleth Layer)
Tidak perlu melakukan multiple JOIN manual. Gunakan view bawaan database:
```sql
SELECT 
    kode_bps, 
    nama_wilayah, 
    tipe, 
    total_rs, 
    total_puskesmas,
    total_tt, 
    jumlah_penduduk_2021, 
    rasio_tt_resmi, 
    kategori_who_resmi,
    proyeksi_penduduk_2026,
    rasio_tt_proyeksi_2026,
    ST_AsGeoJSON(geom)::json AS geojson_polygon
FROM v_choropleth_wilayah;
```

### D. Trigram Fuzzy Search (Toleran Typo <5ms via `pg_trgm`)
```sql
SELECT 
    nama_rs, 
    similarity(nama_rs, :query) AS sim
FROM tbl_rumah_sakit
WHERE similarity(nama_rs, :query) > 0.25
ORDER BY sim DESC 
LIMIT 10;
```

### E. Query Spasial Pencarian Faskes Terdekat (Radius Filter)
```sql
SELECT 
    id_faskes, 
    jenis_faskes, 
    nama, 
    kelas_tipe, 
    alamat, 
    telepon, 
    lat, 
    lng,
    ROUND((ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000)::numeric, 2) AS jarak_km
FROM v_faskes_all
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
