import os
from typing import List, Optional, Dict, Any
import pandas as pd

from backend.app.schemas.katalog import DatasetKatalogItem

EXPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../database/exports"))

DATASETS_METADATA: List[Dict[str, Any]] = [
    {
        "id": "hospitals_clean",
        "judul": "Data Rumah Sakit Bersih Jawa Timur (2026-LIVE)",
        "deskripsi": "447 Rumah Sakit di 38 Kab/Kota Jawa Timur dengan koordinat terverifikasi, enum kepemilikan baku, kapasitas TT, dan layanan unggulan.",
        "domain": "Domain A — Fasilitas Kesehatan",
        "institusi_sumber": "SIRS Kemenkes RI & OpenStreetMap Nominatim",
        "coverage_periode": "2026-LIVE",
        "cakupan_wilayah": "Provinsi Jawa Timur (38 Kab/Kota)",
        "format_tersedia": ["parquet", "csv"],
        "lisensi": "Open Government Data (SIRS Kemenkes)",
        "file_prefix": "hospitals_clean",
    },
    {
        "id": "puskesmas_clean",
        "judul": "Data Puskesmas Bersih Jawa Timur (2024-OFFICIAL)",
        "deskripsi": "977 Puskesmas di 38 Kab/Kota Jawa Timur terbagi atas rawat inap dan non rawat inap beserta koordinat spasial.",
        "domain": "Domain A — Fasilitas Kesehatan",
        "institusi_sumber": "Dinas Kesehatan Provinsi Jawa Timur & OpenData Jatim",
        "coverage_periode": "2024-OFFICIAL",
        "cakupan_wilayah": "Provinsi Jawa Timur (38 Kab/Kota)",
        "format_tersedia": ["parquet", "csv"],
        "lisensi": "Open Government Data Jatim",
        "file_prefix": "puskesmas_clean",
    },
    {
        "id": "bed_ratio_38_kab",
        "judul": "Rasio Tempat Tidur & Proyeksi 2026 38 Kab/Kota",
        "deskripsi": "Agregat kapasitas tempat tidur, rasio resmi basis 2021, dan rasio ketercukupan standar WHO basis proyeksi kependudukan BPS 2026.",
        "domain": "Domain F — Demografi & Spasial",
        "institusi_sumber": "SIRS Kemenkes, Disdukcapil & BPS Jawa Timur",
        "coverage_periode": "2026-PROJECTED",
        "cakupan_wilayah": "Provinsi Jawa Timur (38 Kab/Kota)",
        "format_tersedia": ["parquet", "csv"],
        "lisensi": "Open Government Data",
        "file_prefix": "bed_ratio_38_kab",
    },
    {
        "id": "indicators_jatim",
        "judul": "Indikator Tematik Kesehatan Jawa Timur 2024",
        "deskripsi": "Indikator makro ketersediaan dokter umum dan fasilitas puskesmas per wilayah di Jawa Timur.",
        "domain": "Domain B & C — SDM & Indikator",
        "institusi_sumber": "Dinas Kesehatan Provinsi Jawa Timur",
        "coverage_periode": "2024-OFFICIAL",
        "cakupan_wilayah": "Provinsi Jawa Timur (38 Kab/Kota)",
        "format_tersedia": ["parquet", "csv"],
        "lisensi": "Open Government Data Jatim",
        "file_prefix": "indicators_jatim",
    },
]


def format_file_size(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


class KatalogService:
    @staticmethod
    def get_all_datasets() -> List[DatasetKatalogItem]:
        items: List[DatasetKatalogItem] = []

        for meta in DATASETS_METADATA:
            prefix = meta["file_prefix"]
            pq_path = os.path.join(EXPORTS_DIR, f"{prefix}.parquet")
            csv_path = os.path.join(EXPORTS_DIR, f"{prefix}.csv")

            pq_size = format_file_size(os.path.getsize(pq_path)) if os.path.exists(pq_path) else "N/A"
            csv_size = format_file_size(os.path.getsize(csv_path)) if os.path.exists(csv_path) else "N/A"

            # Profile dataframe shape & columns
            total_rows = 0
            total_cols = 0
            skema: List[Dict[str, str]] = []

            if os.path.exists(pq_path):
                df = pd.read_parquet(pq_path)
                total_rows = len(df)
                total_cols = len(df.columns)
                skema = [{"kolom": col, "tipe": str(dtype)} for col, dtype in df.dtypes.items()][:8]

            items.append(
                DatasetKatalogItem(
                    id=meta["id"],
                    judul=meta["judul"],
                    deskripsi=meta["deskripsi"],
                    domain=meta["domain"],
                    institusi_sumber=meta["institusi_sumber"],
                    coverage_periode=meta["coverage_periode"],
                    cakupan_wilayah=meta["cakupan_wilayah"],
                    format_tersedia=meta["format_tersedia"],
                    total_baris=total_rows,
                    total_kolom=total_cols,
                    file_size_parquet=pq_size,
                    file_size_csv=csv_size,
                    last_updated="2026-08-31",
                    lisensi=meta["lisensi"],
                    skema_ringkas=skema,
                )
            )

        return items

    @staticmethod
    def get_dataset_file_path(dataset_id: str, file_format: str) -> Optional[str]:
        target = next((d for d in DATASETS_METADATA if d["id"] == dataset_id), None)
        if not target:
            return None

        if file_format.lower() not in ["parquet", "csv"]:
            return None

        filename = f"{target['file_prefix']}.{file_format.lower()}"
        full_path = os.path.join(EXPORTS_DIR, filename)

        if os.path.exists(full_path):
            return full_path
        return None
