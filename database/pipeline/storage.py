import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("RawDataStorage")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "raw")

def ensure_source_dir(source_id: str) -> str:
    """Ensure directory for specific source_id exists."""
    target_dir = os.path.join(RAW_DATA_DIR, source_id)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def save_raw_snapshot(source_id: str, data: Any, extension: str = "json") -> str:
    """
    Save fetched raw data with timestamp to database/raw/{source_id}/{YYYYMMDD_HHMMSS}.{ext}.
    Also saves a symlink/pointer copy named 'latest.{ext}' for fast fallback retrieval.
    """
    target_dir = ensure_source_dir(source_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}.{extension}"
    file_path = os.path.join(target_dir, file_name)
    latest_path = os.path.join(target_dir, f"latest.{extension}")

    if extension == "json":
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        mode = "w" if isinstance(data, str) else "wb"
        with open(file_path, mode) as f:
            f.write(data)
        with open(latest_path, mode) as f:
            f.write(data)

    logger.info(f"[Snapshot] Saved raw data for '{source_id}' -> {file_path}")
    return file_path

def load_latest_snapshot(source_id: str, extension: str = "json") -> Tuple[Optional[Any], Optional[str]]:
    """
    Load the most recent snapshot for a source if live API fails.
    Returns: (data, filepath) or (None, None)
    """
    target_dir = os.path.join(RAW_DATA_DIR, source_id)
    latest_path = os.path.join(target_dir, f"latest.{extension}")

    if os.path.exists(latest_path):
        try:
            if extension == "json":
                with open(latest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(latest_path, "r", encoding="utf-8") as f:
                    data = f.read()
            logger.info(f"[Fallback] Loaded fallback snapshot from {latest_path}")
            return data, latest_path
        except Exception as e:
            logger.error(f"[Fallback] Error reading latest snapshot: {e}")

    # Fallback to scanning dir if latest file missing
    if os.path.exists(target_dir):
        files = sorted(
            [f for f in os.listdir(target_dir) if f.endswith(f".{extension}") and f != f"latest.{extension}"],
            reverse=True
        )
        if files:
            fallback_file = os.path.join(target_dir, files[0])
            try:
                if extension == "json":
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        data = f.read()
                logger.info(f"[Fallback] Loaded latest snapshot from {fallback_file}")
                return data, fallback_file
            except Exception as e:
                logger.error(f"[Fallback] Error reading {fallback_file}: {e}")

    logger.warning(f"[Fallback] No local snapshots available for '{source_id}'")
    return None, None
