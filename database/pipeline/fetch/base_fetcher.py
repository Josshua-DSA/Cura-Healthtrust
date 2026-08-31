"""
BaseFetcher — Abstract base class untuk semua data fetcher.
Sesuai RULES.md Seksi 2.2: Setiap sumber data punya satu Fetcher class yang inherit dari BaseFetcher.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import requests

from exceptions import FetchError
from pipeline.storage import save_raw_snapshot, load_latest_snapshot

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """
    Base class untuk semua data fetcher Cura.
    Subclass wajib implement fetch() dan source_id.

    Alur: run() → fetch() → _save() → return records
    Fallback: jika fetch() gagal, load snapshot terakhir dari raw/.
    """

    source_id: str  # wajib didefinisikan di subclass

    HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (HealthTrust Pipeline; Linux x86_64) AppleWebKit/537.36"
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    @abstractmethod
    def fetch(self) -> Tuple[Any, bool]:
        """
        Ambil data dari sumber. Return (data, is_live).
        Raise FetchError jika gagal dan tidak ada fallback.
        """
        ...

    def _fetch_url(self, url: str) -> Any:
        """Helper: GET request dengan error handling standar."""
        try:
            logger.info(f"Fetching live data from {url} ...")
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            save_raw_snapshot(self.source_id, data, extension="json")
            return data
        except requests.HTTPError as e:
            raise FetchError(
                f"[{self.source_id}] HTTP {e.response.status_code}: {url}"
            ) from e
        except requests.Timeout:
            raise FetchError(
                f"[{self.source_id}] Request timeout: {url}"
            ) from None
        except Exception as e:
            raise FetchError(
                f"[{self.source_id}] Fetch failed: {e}"
            ) from e

    def _load_fallback(self) -> Tuple[Optional[Any], Optional[str]]:
        """Load snapshot terakhir dari raw/ sebagai fallback."""
        return load_latest_snapshot(self.source_id, extension="json")

    def run(self) -> Tuple[Any, bool]:
        """
        Entry point: fetch live → fallback snapshot jika gagal.
        Return (data, is_live).
        """
        try:
            return self.fetch()
        except FetchError as e:
            logger.warning(f"Live fetch failed for '{self.source_id}': {e}. Attempting fallback...")
            fallback_data, path = self._load_fallback()
            if fallback_data is not None:
                return fallback_data, False
            raise FetchError(
                f"Failed to fetch live data and no local snapshot available for {self.source_id}"
            ) from e
