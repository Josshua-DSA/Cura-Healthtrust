from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from backend.app.schemas.ask import AskDataRequest, AskDataResponse, AskDataCitation
from backend.app.services.wilayah_service import compute_who_category


class AskDataService:
    @staticmethod
    async def process_query(db: AsyncSession, request: AskDataRequest) -> AskDataResponse:
        query_text = request.query.lower()

        citations: List[AskDataCitation] = []
        grounding_data: Dict[str, Any] = {}

        # 1. Wilayah / Choropleth Context
        wilayah_clause = ""
        params: Dict[str, Any] = {}
        if request.target_wilayah:
            wilayah_clause = "WHERE kode_bps = :kode_bps"
            params["kode_bps"] = request.target_wilayah

        query_w = text(f"""
            SELECT 
                kode_bps, 
                nama_wilayah, 
                total_rs, 
                total_puskesmas, 
                total_tt, 
                rasio_tt_resmi, 
                rasio_tt_proyeksi_2026, 
                kategori_who_resmi
            FROM v_choropleth_wilayah
            {wilayah_clause}
            ORDER BY rasio_tt_proyeksi_2026 DESC
            LIMIT 10;
        """)
        res_w = await db.execute(query_w, params)
        raw_rows = res_w.mappings().all()

        rows_w = []
        for r in raw_rows:
            r_dict = dict(r)
            r_proj = float(r_dict["rasio_tt_proyeksi_2026"] or 0.0)
            r_dict["kategori_who_proyeksi_2026"] = compute_who_category(r_proj)
            rows_w.append(r_dict)

        grounding_data["wilayah_metrics"] = rows_w

        citations.append(
            AskDataCitation(
                dataset_name="v_choropleth_wilayah (BPS & SIRS Kemenkes)",
                source_institution="BPS Jawa Timur & SIRS Kemenkes",
                coverage_periode="2026-PROJECTED",
                relevance_note="Digunakan untuk data rasio tempat tidur dan proyeksi kependudukan wilayah.",
            )
        )

        # 2. SDM / Dokter Context
        if "dokter" in query_text or "sdm" in query_text or "nakes" in query_text:
            query_sdm = text("""
                SELECT w.nama_wilayah, ind.nilai as jumlah_dokter, ind.satuan
                FROM tbl_indikator_kesehatan ind
                JOIN ref_wilayah w ON w.kode_bps = ind.kode_bps
                WHERE ind.topik = 'Tenaga Medis'
                ORDER BY ind.nilai DESC
                LIMIT 5;
            """)
            res_sdm = await db.execute(query_sdm)
            grounding_data["top_dokter_wilayah"] = [dict(r) for r in res_sdm.mappings().all()]

            citations.append(
                AskDataCitation(
                    dataset_name="tbl_indikator_kesehatan (Dinkes Jatim)",
                    source_institution="Dinas Kesehatan Provinsi Jawa Timur",
                    coverage_periode="2024-OFFICIAL",
                    relevance_note="Digunakan untuk data jumlah dokter umum per kabupaten/kota.",
                )
            )

        # 3. Formulate Natural Language Answer
        answer_parts = []
        if request.target_wilayah and rows_w:
            w = rows_w[0]
            answer_parts.append(
                f"Berdasarkan data resmi untuk {w['nama_wilayah']} (Kode BPS: {w['kode_bps']}), terdapat {w['total_rs']} Rumah Sakit dan {w['total_puskesmas']} Puskesmas dengan total kapasitas {w['total_tt']} tempat tidur."
            )
            answer_parts.append(
                f"Rasio ketercukupan tempat tidur proyeksi tahun 2026 adalah {w['rasio_tt_proyeksi_2026']} TT per 1.000 penduduk (Kategori WHO: {w['kategori_who_proyeksi_2026'].upper()})."
            )
        else:
            top_w = rows_w[0] if rows_w else None
            answer_parts.append(
                f"Berdasarkan dataset platform Cura Jawa Timur, sistem memetakan 38 Kabupaten/Kota dengan 447 Rumah Sakit dan 977 Puskesmas aktif."
            )
            if top_w:
                answer_parts.append(
                    f"Wilayah dengan rasio fasilitas tertinggi dalam sampel adalah {top_w['nama_wilayah']} ({top_w['rasio_tt_proyeksi_2026']} TT / 1.000 pddk)."
                )

        if "top_dokter_wilayah" in grounding_data and grounding_data["top_dokter_wilayah"]:
            top_doc = grounding_data["top_dokter_wilayah"][0]
            answer_parts.append(
                f"Untuk tenaga medis dokter umum, wilayah dengan jumlah tertinggi adalah {top_doc['nama_wilayah']} ({top_doc['jumlah_dokter']} orang)."
            )

        final_answer = " ".join(answer_parts)

        return AskDataResponse(
            query=request.query,
            answer=final_answer,
            grounding_data=grounding_data,
            citations=citations,
            disclaimer="Insight ini dihasilkan AI berdasarkan data resmi Jawa Timur (SIRS Kemenkes & OpenData Jatim).",
        )
