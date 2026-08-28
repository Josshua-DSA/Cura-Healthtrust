import logging
from typing import List, Dict, Any
from pipeline.loader import (
    get_session, init_db, upsert_rumah_sakit,
    upsert_ref_wilayah, upsert_penduduk, upsert_indikator_kesehatan,
    recompute_agregat_wilayah
)

logger = logging.getLogger("LoadToPostGIS")

def load_all_to_postgis(
    rs_records: List[Dict[str, Any]],
    wilayah_records: List[Dict[str, Any]],
    penduduk_records: List[Dict[str, Any]],
    indikator_records: List[Dict[str, Any]],
    rasio_raw_list: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Direct loader to PostgreSQL/PostGIS with spatial indexing & precomputed aggregates.
    """
    init_db()
    session = get_session()
    try:
        loaded_wilayah = upsert_ref_wilayah(session, wilayah_records) if wilayah_records else 0
        loaded_penduduk = upsert_penduduk(session, penduduk_records) if penduduk_records else 0
        loaded_rs = upsert_rumah_sakit(session, rs_records) if rs_records else 0
        loaded_ind = upsert_indikator_kesehatan(session, indikator_records) if indikator_records else 0
        recompute_agregat_wilayah(session, tahun=2024, rasio_data_list=rasio_raw_list)

        return {
            "wilayah": loaded_wilayah,
            "penduduk": loaded_penduduk,
            "rumah_sakit": loaded_rs,
            "indikator": loaded_ind
        }
    finally:
        session.close()
