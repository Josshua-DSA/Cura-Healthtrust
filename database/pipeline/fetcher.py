"""
SIRS Kemenkes Fetchers — OOP classes sesuai RULES.md Seksi 2.2.
Backward-compatible: fungsi legacy fetch_sirs_data_rs(), fetch_all_sources() tetap tersedia.
"""

import logging
from typing import Any, Dict, Tuple

from pipeline.fetch.base_fetcher import BaseFetcher
from exceptions import FetchError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DataFetcher")


# ─── OOP Fetcher Classes ───────────────────────────────────────────


class SirsRsListFetcher(BaseFetcher):
    """Fetcher untuk daftar 447+ RS di Jawa Timur dari SIRS Kemenkes."""

    source_id = "sirs_kemenkes_list"
    URL = "https://sirs.kemkes.go.id/fo/home/list_prop_noncovid?id=35"

    def fetch(self) -> Tuple[Any, bool]:
        data = self._fetch_url(self.URL)
        return data, True


class SirsRekapRsFetcher(BaseFetcher):
    """Fetcher untuk rekap kepemilikan dan detail RS."""

    source_id = "sirs_kemenkes_rekap"
    URL = "https://sirs.kemkes.go.id/fo/home/rekap_rs_all?id=35"

    def fetch(self) -> Tuple[Any, bool]:
        data = self._fetch_url(self.URL)
        return data, True


class SirsRasioTtFetcher(BaseFetcher):
    """Fetcher untuk rasio tempat tidur per 1000 penduduk per 38 Kab/Kota."""

    source_id = "sirs_kemenkes_rasio_tt"
    URL = "https://sirs.kemkes.go.id/fo/mapgeo/rasio_tt?id=35"

    def fetch(self) -> Tuple[Any, bool]:
        data = self._fetch_url(self.URL)
        return data, True


class SirsGeojsonFetcher(BaseFetcher):
    """Fetcher untuk GeoJSON batas wilayah 38 Kab/Kota Jawa Timur."""

    source_id = "sirs_kemenkes_geojson"
    URL = "https://sirs.kemkes.go.id/fo/mapgeo/koordinat?id=35&mapfile=json%2Fprovinsi.json"

    def fetch(self) -> Tuple[Any, bool]:
        data = self._fetch_url(self.URL)
        return data, True


# ─── Backward-Compatible Legacy Functions ──────────────────────────


def fetch_sirs_data_rs() -> Tuple[Dict[str, Any], bool]:
    """Legacy wrapper: fetch RS list via OOP class."""
    return SirsRsListFetcher().run()


def fetch_sirs_rekap_rs() -> Tuple[Dict[str, Any], bool]:
    """Legacy wrapper: fetch rekap RS via OOP class."""
    return SirsRekapRsFetcher().run()


def fetch_sirs_rasio_tt() -> Tuple[Dict[str, Any], bool]:
    """Legacy wrapper: fetch rasio TT via OOP class."""
    return SirsRasioTtFetcher().run()


def fetch_sirs_geojson() -> Tuple[Dict[str, Any], bool]:
    """Legacy wrapper: fetch GeoJSON via OOP class."""
    return SirsGeojsonFetcher().run()


def fetch_all_sources() -> Dict[str, Any]:
    """Fetch all primary datasets and return consolidated dict."""
    logger.info("=" * 60)
    logger.info(" [HealthTrust Pipeline] Ingesting All Sources to Raw Storage")
    logger.info("=" * 60)

    results = {}

    # 1. RS List & Koordinat
    rs_list, live1 = fetch_sirs_data_rs()
    results["rs_list"] = {"count": len(rs_list.get("rs", [])), "is_live": live1}

    # 2. Rekap RS (Pemilik)
    rekap_rs, live2 = fetch_sirs_rekap_rs()
    results["rekap_rs"] = {"count": len(rekap_rs.get("data", [])), "is_live": live2}

    # 3. Rasio TT & Wilayah
    rasio_tt, live3 = fetch_sirs_rasio_tt()
    results["rasio_tt"] = {"count": len(rasio_tt.get("wilayah", [])), "is_live": live3}

    # 4. GeoJSON Batas Wilayah
    geojson_data, live4 = fetch_sirs_geojson()
    results["geojson"] = {"count": len(geojson_data.get("features", [])), "is_live": live4}

    logger.info("=" * 60)
    logger.info(f" Ingestion Summary: {results}")
    logger.info("=" * 60)
    return results


if __name__ == "__main__":
    fetch_all_sources()
