# PRD.md — Product Requirements Document
# Cura: HealthTrust Facilities
> Versi 1.0 — Fase MVP

---

## 1. Latar Belakang & Masalah

Data fasilitas kesehatan (khususnya rumah sakit) di Jawa Timur tersebar di berbagai portal pemerintah — Open Data Jatim, SIRS Kemenkes, BPS, SATUSEHAT — dalam format yang tidak konsisten dan tidak mudah diakses oleh non-teknis. Pemda, mahasiswa, peneliti, dan masyarakat umum kesulitan menjawab pertanyaan sederhana seperti:

- "Kabupaten mana di Jatim yang paling kekurangan fasilitas RS?"
- "Berapa rasio tempat tidur per 1.000 penduduk di Kab. Sampang?"
- "Mana saja RS kelas A di Jawa Timur?"

**Cura** hadir sebagai portal eksplorasi data publik yang menjembatani gap ini — tanpa memerlukan kemampuan coding dari penggunanya.

---

## 2. Target Pengguna

| Segmen | Kebutuhan Utama |
|---|---|
| **Mahasiswa/Akademisi** | Data untuk tugas akhir, penelitian, analisis kesehatan wilayah |
| **Pemda / Dinas Kesehatan** | Dashboard pemetaan kebutuhan fasilitas, bahan kebijakan |
| **Masyarakat Umum** | Mencari informasi RS terdekat, kelas, dan fasilitas |
| **Jurnalis / NGO** | Data untuk investigasi atau advokasi kesehatan daerah |

---

## 3. Tujuan Produk

**Tujuan utama MVP:**
Memungkinkan siapapun mengeksplorasi data fasilitas kesehatan (rumah sakit) di Jawa Timur secara visual, tanpa coding, melalui browser.

**Metrik keberhasilan MVP:**
- Data ≥ 200 RS di Jawa Timur berhasil di-ingest dan dibersihkan
- Peta choropleth rasio TT/penduduk per 38 kab/kota Jatim dapat ditampilkan
- Fitur filter katalog berfungsi (kelas, kab/kota, kepemilikan)
- Fitur "Ask Data" menghasilkan insight yang relevan dengan konteks data

---

## 4. Scope MVP

### 4.1 Yang ADA di MVP

**[F01] Katalog Fasilitas Kesehatan**
- Daftar RS dengan card view
- Filter: kelas (A/B/C/D), kab/kota, jenis kepemilikan (pemerintah/swasta)
- Search by nama RS
- Setiap item menampilkan: nama, alamat, kelas, kepemilikan, jumlah TT
- Setiap dataset menampilkan metadata: sumber, lisensi, tanggal update terakhir, data dictionary link

**[F02] Halaman Detail RS**
- Informasi lengkap satu RS
- Lokasi di mini-map (Leaflet marker)
- Statistik: jumlah TT, layanan tersedia, dokter spesialis (jika ada)
- Tautan ke sumber data asli

**[F03] Peta Interaktif Jatim**
- Choropleth layer: rasio tempat tidur per 1.000 penduduk per kab/kota
- Marker layer: lokasi setiap RS (toggle on/off)
- Popup per RS: nama, kelas, kepemilikan
- Popup per wilayah: jumlah RS, total TT, rasio TT/penduduk
- Kontrol: toggle layer, legenda warna, zoom

**[F04] Panel EDA (Exploratory Data Analysis)**
- Distribusi kelas RS di Jatim (pie/bar chart)
- Jumlah RS per kab/kota (bar chart horizontal)
- Rasio pemerintah vs swasta (donut chart)
- Perbandingan antar wilayah (grouped bar)
- Tabel data mentah dengan sort & filter kolom

**[F05] Trend View**
- Pertumbuhan jumlah RS per tahun (2019–2024) di Jatim
- Filter per kab/kota

**[F06] Ask Data (AI Insight)**
- Input: pertanyaan bebas dalam Bahasa Indonesia
- Output: penjelasan natural language berbasis data yang ada
- Contoh: *"Wilayah mana yang paling kekurangan RS?"*
- Disclaimer: "Insight ini dihasilkan oleh AI berdasarkan data yang tersedia"

**[F07] Shareable View**
- Setiap kombinasi filter/view menghasilkan URL unik yang bisa di-share
- URL encode state: halaman, filter aktif, zoom peta

### 4.2 Yang TIDAK ADA di MVP (post-MVP)

- Upload dataset custom oleh pengguna
- Login / autentikasi pengguna
- Clustering ML / anomaly detection
- Integrasi data BPJS (klaim, iuran)
- Data faskes selain RS (Puskesmas, klinik, apotek)
- Notifikasi / alert data baru
- Export hasil analisis ke PDF

---

## 5. User Stories

### Sebagai Mahasiswa
- Saya ingin **melihat peta distribusi RS di Jatim** sehingga saya bisa mengidentifikasi wilayah under-served untuk topik skripsi saya.
- Saya ingin **mengunduh data mentah** sehingga saya bisa mengolahnya lebih lanjut di R/Python.

### Sebagai Pemda / Dinas Kesehatan
- Saya ingin **melihat rasio tempat tidur per penduduk per kab/kota** sehingga saya bisa memprioritaskan pembangunan RS baru.
- Saya ingin **membandingkan dua kabupaten** sehingga saya punya dasar argumen untuk alokasi anggaran.

### Sebagai Masyarakat Umum
- Saya ingin **mencari RS kelas B di Malang** sehingga saya tahu pilihan faskes rujukan saya.
- Saya ingin **tanya "RS terdekat dari Situbondo yang punya ICU"** dan mendapat jawaban langsung.

### Sebagai Jurnalis
- Saya ingin **share URL halaman analisis tertentu** ke rekan saya sehingga mereka melihat data yang sama persis.

---

## 6. Persyaratan Non-Fungsional

| Aspek | Requirement |
|---|---|
| **Performa** | Halaman katalog load < 2 detik (data dari backend, bukan render SSR) |
| **Aksesibilitas** | Dapat diakses di mobile browser (responsive layout) |
| **Data freshness** | Metadata menampilkan tanggal update terakhir per sumber |
| **Transparansi** | Setiap insight AI wajib disertai disclaimer dan konteks data yang digunakan |
| **Lisensi** | Setiap dataset menampilkan lisensi sumber aslinya |
| **Offline-safe** | Jika backend tidak tersedia, frontend menampilkan pesan error yang informatif |

---

## 7. Data Requirements

### 7.1 Dataset Wajib (MVP tidak bisa jalan tanpa ini)

| Dataset | Sumber | Field Minimum |
|---|---|---|
| Daftar RS Jatim | api.co.id / SIRS | nama, alamat, kelas, lat, lng, kepemilikan, jumlah_tt |
| Batas wilayah kab/kota Jatim | GeoJSON superpikar | kode_bps, nama, geometry |
| Penduduk per kab/kota | BPS Jatim | kode_bps, tahun, jumlah_penduduk |

### 7.2 Dataset Tambahan (memperkaya fitur)

| Dataset | Sumber | Menambah Fitur |
|---|---|---|
| Jumlah RS per kab/kota historis | data.go.id / BPS | Trend view |
| Rasio TT per 1.000 penduduk | Dihitung dari join | Choropleth peta |
| Data faskes Dinkes Jatim | opendata.jatimprov.go.id | Coverage check, validasi silang |

### 7.3 Metadata Wajib per Dataset

Setiap dataset yang ditampilkan ke pengguna wajib memiliki:
- `source_name` — nama institusi penyedia
- `source_url` — URL asli sumber
- `license` — jenis lisensi data
- `last_updated` — tanggal update terakhir di sumber
- `coverage` — cakupan wilayah & periode
- `data_dictionary` — deskripsi tiap field/kolom
- `limitations` — batasan / catatan penggunaan data

---

## 8. Halaman & Navigasi

```
/                   → index.html        Katalog + Search
/map                → map.html          Peta interaktif
/explorer           → explorer.html     EDA & chart
/detail?id={id}     → detail.html       Detail satu RS
/ask                → ask.html          Ask Data (AI)
```

Navigasi top bar: Logo Cura | Katalog | Peta | Eksplorasi | Tanya Data

---

## 9. Konvensi & Standar

- **Bahasa UI:** Bahasa Indonesia
- **Format angka:** Titik sebagai pemisah ribuan (1.000), koma sebagai desimal (0,5)
- **Koordinat:** WGS84 (lat/lng decimal degrees)
- **Kode wilayah:** Kode BPS 4 digit (contoh: 3578 = Kota Surabaya)
- **Kelas RS:** Enum string: `"A"`, `"B"`, `"C"`, `"D"`, `"tidak_diketahui"`
- **Kepemilikan RS:** Enum string: `"pemerintah"`, `"swasta"`, `"tni_polri"`, `"lainnya"`

---

## 10. Prioritas Fitur (MoSCoW)

| Prioritas | Fitur |
|---|---|
| **Must Have** | F01 Katalog, F03 Peta, F07 Metadata per dataset |
| **Should Have** | F04 EDA Panel, F02 Detail RS, F06 Ask Data |
| **Could Have** | F05 Trend, F07 Shareable URL |
| **Won't Have (MVP)** | Upload user, Login, ML clustering |