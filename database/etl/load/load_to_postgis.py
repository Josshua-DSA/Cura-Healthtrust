import logging
from typing import List, Dict, Any, Optional
from pipeline.loader import (
    get_session, init_db, upsert_rumah_sakit, upsert_puskesmas,
    upsert_ref_wilayah, upsert_penduduk, upsert_indikator_kesehatan,
    upsert_tenaga_kesehatan, upsert_pasien_morbiditas,
    upsert_indikator_kia, upsert_penyakit_surveillance,
    upsert_alert_rules, upsert_alert_events,
    recompute_agregat_wilayah
)

logger = logging.getLogger("LoadToPostGIS")

def load_all_to_postgis(
    rs_records: List[Dict[str, Any]],
    wilayah_records: List[Dict[str, Any]],
    penduduk_records: List[Dict[str, Any]],
    indikator_records: List[Dict[str, Any]],
    rasio_raw_list: List[Dict[str, Any]],
    puskesmas_records: Optional[List[Dict[str, Any]]] = None,
    nakes_records: Optional[List[Dict[str, Any]]] = None,
    morbiditas_records: Optional[List[Dict[str, Any]]] = None,
    kia_records: Optional[List[Dict[str, Any]]] = None,
    surveillance_records: Optional[List[Dict[str, Any]]] = None,
    alert_rules_records: Optional[List[Dict[str, Any]]] = None,
    alert_events_records: Optional[List[Dict[str, Any]]] = None
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
        loaded_pkm = upsert_puskesmas(session, puskesmas_records) if puskesmas_records else 0
        loaded_nakes = upsert_tenaga_kesehatan(session, nakes_records) if nakes_records else 0
        loaded_morbid = upsert_pasien_morbiditas(session, morbiditas_records) if morbiditas_records else 0
        loaded_ind = upsert_indikator_kesehatan(session, indikator_records) if indikator_records else 0
        loaded_kia = upsert_indikator_kia(session, kia_records) if kia_records else 0
        loaded_surv = upsert_penyakit_surveillance(session, surveillance_records) if surveillance_records else 0
        loaded_rules = upsert_alert_rules(session, alert_rules_records) if alert_rules_records else 0
        loaded_events = upsert_alert_events(session, alert_events_records) if alert_events_records else 0
        
        recompute_agregat_wilayah(session, tahun=2024, rasio_data_list=rasio_raw_list)

        return {
            "wilayah": loaded_wilayah,
            "penduduk": loaded_penduduk,
            "rumah_sakit": loaded_rs,
            "puskesmas": loaded_pkm,
            "tenaga_kesehatan": loaded_nakes,
            "pasien_morbiditas": loaded_morbid,
            "indikator": loaded_ind,
            "indikator_kia": loaded_kia,
            "surveillance": loaded_surv,
            "alert_rules": loaded_rules,
            "alert_events": loaded_events
        }
    finally:
        session.close()
