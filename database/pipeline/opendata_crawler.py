"""
Open Data Jatim Crawler — OOP class + legacy functions sesuai RULES.md Seksi 2.2.
Backward-compatible: fungsi legacy crawl_and_parse_opendata_csv() dan match_kode_bps() tetap tersedia.
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from pipeline.fetch.base_fetcher import BaseFetcher
from pipeline.storage import save_raw_snapshot
from exceptions import FetchError

logger = logging.getLogger("OpenDataJatimCrawler")

# Target Open Data Jatim Datasets (Puskesmas, Nakes, Faskes)
TARGET_DATASET_IDS = [
    {"id": "13988", "topik": "Puskesmas", "nama": "Jumlah Puskesmas Rawat Inap & Non Rawat Inap"},
    {"id": "3505", "topik": "Fasilitas Kesehatan", "nama": "Jumlah Tempat Tidur Rumah Sakit"},
    {"id": "3504", "topik": "Tenaga Medis", "nama": "Persebaran Tenaga Kesehatan Jatim"}
]

# Map nama wilayah kab/kota to kode_bps (3501 - 3579)
WILAYAH_TO_KODE_BPS = {
    "pacitan": "3501", "ponorogo": "3502", "trenggalek": "3503", "tulungagung": "3504",
    "blitar": "3505", "kabupaten blitar": "3505", "kota blitar": "3572",
    "kediri": "3506", "kabupaten kediri": "3506", "kota kediri": "3571",
    "malang": "3507", "kabupaten malang": "3507", "kota malang": "3573", "kota batu": "3579", "batu": "3579",
    "lumajang": "3508", "jember": "3509", "banyuwangi": "3510", "bondowoso": "3511",
    "situbondo": "3512", "probolinggo": "3513", "kabupaten probolinggo": "3513", "kota probolinggo": "3574",
    "pasuruan": "3514", "kabupaten pasuruan": "3514", "kota pasuruan": "3575",
    "sidoarjo": "3515", "mojokerto": "3516", "kabupaten mojokerto": "3516", "kota mojokerto": "3576",
    "jombang": "3517", "nganjuk": "3518", "madiun": "3519", "kabupaten madiun": "3519", "kota madiun": "3577",
    "magetan": "3520", "ngawi": "3521", "bojonegoro": "3522", "tuban": "3523",
    "lamongan": "3524", "gresik": "3525", "bangkalan": "3526", "sampang": "3527",
    "pamekasan": "3528", "sumenep": "3529", "surabaya": "3578", "kota surabaya": "3578"
}


# ─── Standalone Helper Functions ───────────────────────────────────


def match_kode_bps(wilayah_name: str) -> Optional[str]:
    """Normalize raw region string to 4-digit BPS code with fuzzy support."""
    if not wilayah_name:
        return None
    cleaned = re.sub(r'[^a-zA-Z\s]', '', str(wilayah_name)).strip().lower()

    # 1. Direct match
    if cleaned in WILAYAH_TO_KODE_BPS:
        return WILAYAH_TO_KODE_BPS[cleaned]

    # 2. Strip 'kabupaten ' prefix
    if cleaned.startswith("kabupaten "):
        bare = cleaned.replace("kabupaten ", "").strip()
        if bare in WILAYAH_TO_KODE_BPS:
            return WILAYAH_TO_KODE_BPS[bare]

    # 3. Strip 'kota ' prefix
    if cleaned.startswith("kota "):
        bare = cleaned.replace("kota ", "").strip()
        if f"kota {bare}" in WILAYAH_TO_KODE_BPS:
            return WILAYAH_TO_KODE_BPS[f"kota {bare}"]
        if bare in WILAYAH_TO_KODE_BPS:
            return WILAYAH_TO_KODE_BPS[bare]

    return None


# ─── OOP Fetcher Class ────────────────────────────────────────────


class OpenDataJatimFetcher(BaseFetcher):
    """
    Fetcher untuk Open Data Jatim (Indikator Kesehatan Daerah).
    Sesuai RULES.md Seksi 2.2: inherit dari BaseFetcher.

    Strategi: Coba fetch metadata API → Fallback ke local seed CSV.
    """

    source_id = "opendata_jatim"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self._seed_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "seeds", "indikator_kesehatan_jatim.csv"
        )

    def fetch(self) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch metadata dari API dan parse local seed CSV."""
        # Coba fetch metadata API (non-critical)
        self._fetch_api_metadata()

        # Parse structured seed CSV
        records = self._parse_seed_csv()
        return records, True

    def _fetch_api_metadata(self) -> None:
        """Fetch dataset metadata dari API Open Data Jatim (non-critical)."""
        try:
            url = "https://opendata.jatimprov.go.id/api/datasets/13988"
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                meta = r.json().get("data", {})
                save_raw_snapshot("opendata_jatim_meta_13988", meta)
        except Exception as e:
            logger.warning(f"[OpenData Jatim] Error fetching dataset metadata: {e}")

    def _parse_seed_csv(self) -> List[Dict[str, Any]]:
        """Parse local structured seed CSV ke format indikator."""
        records: List[Dict[str, Any]] = []

        if not os.path.exists(self._seed_path):
            logger.warning(f"[OpenData Jatim] Seed file not found: {self._seed_path}")
            return records

        logger.info(f"[OpenData Jatim] Ingesting structured health indicators from {self._seed_path}...")
        df = pd.read_csv(self._seed_path)

        for _, row in df.iterrows():
            kbps = match_kode_bps(row.get("nama_wilayah", "")) or str(row.get("kode_bps", ""))
            if kbps and len(kbps) == 4:
                records.append({
                    "kode_bps": kbps,
                    "nama_wilayah": str(row.get("nama_wilayah", "")),
                    "tahun": int(row.get("tahun", 2024)),
                    "topik": str(row.get("topik", "Fasilitas Kesehatan")),
                    "nama_indikator": str(row.get("nama_indikator", "Puskesmas")),
                    "nilai": float(row.get("nilai", 0)),
                    "satuan": str(row.get("satuan", "Unit")),
                    "sumber_data": "Dinas Kesehatan Provinsi Jawa Timur",
                    "coverage_periode": "2024-OFFICIAL"
                })

        logger.info(f"[OpenData Jatim] Successfully prepared {len(records)} indicator records.")
        return records


# ─── Backward-Compatible Legacy Function ──────────────────────────


def crawl_and_parse_opendata_csv() -> List[Dict[str, Any]]:
    """Legacy wrapper: crawl Open Data Jatim via OOP class."""
    fetcher = OpenDataJatimFetcher()
    records, _ = fetcher.run()
    return records
