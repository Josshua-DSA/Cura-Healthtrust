from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.schemas.statistik import (
    ExecutiveSummaryKPI,
    AccessibilityMetrics,
    WilayahCompareResponse,
)


class StatistikService:
    @staticmethod
    async def get_executive_summary(db: AsyncSession) -> ExecutiveSummaryKPI:
        query_kpi = text("""
            SELECT 
                SUM(total_rs)::int as total_rs,
                SUM(total_puskesmas)::int as total_puskesmas,
                SUM(total_tt)::int as total_tt,
                SUM(jumlah_penduduk_2021)::int as total_pddk_2021,
                SUM(proyeksi_penduduk_2026)::int as total_pddk_2026,
                ROUND(AVG(rasio_tt_resmi)::numeric, 2)::float as avg_rasio_resmi,
                ROUND(AVG(rasio_tt_proyeksi_2026)::numeric, 2)::float as avg_rasio_2026,
                COUNT(CASE WHEN kategori_who_resmi = 'hijau' THEN 1 END)::int as resmi_hijau,
                COUNT(CASE WHEN kategori_who_resmi = 'kuning' THEN 1 END)::int as resmi_kuning,
                COUNT(CASE WHEN kategori_who_resmi = 'merah' THEN 1 END)::int as resmi_merah,
                COUNT(CASE WHEN rasio_tt_proyeksi_2026 >= 1.0 THEN 1 END)::int as proj_hijau,
                COUNT(CASE WHEN rasio_tt_proyeksi_2026 >= 0.7 AND rasio_tt_proyeksi_2026 < 1.0 THEN 1 END)::int as proj_kuning,
                COUNT(CASE WHEN rasio_tt_proyeksi_2026 < 0.7 THEN 1 END)::int as proj_merah
            FROM v_choropleth_wilayah;
        """)
        res = await db.execute(query_kpi)
        kpi = res.mappings().first()

        # Total Dokter
        query_dokter = text("""
            SELECT SUM(nilai)::int FROM tbl_indikator_kesehatan WHERE nama_indikator ILIKE '%Dokter%';
        """)
        total_dokter = await db.scalar(query_dokter) or 0

        # Top 5 Wilayah by Faskes
        query_top = text("""
            SELECT nama_wilayah, (total_rs + total_puskesmas)::int as total_faskes, total_tt::int as total_tt
            FROM v_choropleth_wilayah
            ORDER BY total_faskes DESC
            LIMIT 5;
        """)
        top_res = await db.execute(query_top)
        top_list = [dict(r) for r in top_res.mappings().all()]

        t_rs = int(kpi["total_rs"] or 0)
        t_pkm = int(kpi["total_puskesmas"] or 0)

        return ExecutiveSummaryKPI(
            total_rs=t_rs,
            total_puskesmas=t_pkm,
            total_faskes=t_rs + t_pkm,
            total_tempat_tidur=int(kpi["total_tt"] or 0),
            total_dokter=int(total_dokter),
            total_penduduk_2021=int(kpi["total_pddk_2021"] or 0),
            total_proyeksi_penduduk_2026=int(kpi["total_pddk_2026"] or 0),
            rasio_tt_rata_rata_resmi=float(kpi["avg_rasio_resmi"] or 0.0),
            rasio_tt_rata_rata_2026=float(kpi["avg_rasio_2026"] or 0.0),
            distribusi_kategori_who_resmi={
                "hijau": int(kpi["resmi_hijau"] or 0),
                "kuning": int(kpi["resmi_kuning"] or 0),
                "merah": int(kpi["resmi_merah"] or 0),
            },
            distribusi_kategori_who_2026={
                "hijau": int(kpi["proj_hijau"] or 0),
                "kuning": int(kpi["proj_kuning"] or 0),
                "merah": int(kpi["proj_merah"] or 0),
            },
            top_wilayah_faskes=top_list,
        )

    @staticmethod
    async def get_accessibility_metrics(db: AsyncSession) -> AccessibilityMetrics:
        query_under = text("""
            SELECT kode_bps, nama_wilayah, rasio_tt_proyeksi_2026::float as rasio, total_tt::int as total_tt, proyeksi_penduduk_2026::int as penduduk
            FROM v_choropleth_wilayah
            WHERE rasio_tt_proyeksi_2026 < 0.7
            ORDER BY rasio_tt_proyeksi_2026 ASC;
        """)
        under_res = await db.execute(query_under)
        under_list = [dict(r) for r in under_res.mappings().all()]

        query_optimal = text("""
            SELECT kode_bps, nama_wilayah, rasio_tt_proyeksi_2026::float as rasio, total_tt::int as total_tt, proyeksi_penduduk_2026::int as penduduk
            FROM v_choropleth_wilayah
            WHERE rasio_tt_proyeksi_2026 >= 1.0
            ORDER BY rasio_tt_proyeksi_2026 DESC
            LIMIT 10;
        """)
        opt_res = await db.execute(query_optimal)
        opt_list = [dict(r) for r in opt_res.mappings().all()]

        query_avg = text("""
            SELECT 
                ROUND(AVG(rasio_tt_proyeksi_2026)::numeric, 2)::float as avg_tt,
                ROUND((SUM(ind.nilai) / SUM(c.proyeksi_penduduk_2026) * 1000.0)::numeric, 2)::float as avg_dokter
            FROM v_choropleth_wilayah c
            LEFT JOIN tbl_indikator_kesehatan ind ON ind.kode_bps = c.kode_bps AND ind.topik = 'Tenaga Medis';
        """)
        avg_res = await db.execute(query_avg)
        avg_row = avg_res.mappings().first()

        gap_text = f"Terdapat {len(under_list)} wilayah berstatus defisit kritis tempat tidur (<0.7 TT / 1.000 pddk) pada proyeksi 2026."

        return AccessibilityMetrics(
            under_served_districts=under_list,
            optimal_served_districts=opt_list,
            avg_rasio_dokter_jatim=float(avg_row["avg_dokter"] or 0.0),
            avg_rasio_tt_jatim=float(avg_row["avg_tt"] or 0.0),
            gap_summary=gap_text,
        )

    @staticmethod
    async def compare_wilayah(db: AsyncSession, kode_bps_a: str, kode_bps_b: str) -> WilayahCompareResponse:
        query = text("""
            SELECT 
                w.kode_bps,
                w.nama_wilayah,
                w.tipe::text as tipe,
                c.total_rs::int as total_rs,
                c.total_puskesmas::int as total_puskesmas,
                c.total_tt::int as total_tt,
                c.jumlah_penduduk_2021::int as jumlah_penduduk_2021,
                c.proyeksi_penduduk_2026::int as proyeksi_penduduk_2026,
                c.rasio_tt_resmi::float as rasio_tt_resmi,
                c.rasio_tt_proyeksi_2026::float as rasio_tt_proyeksi_2026,
                COALESCE(MAX(CASE WHEN ind.nama_indikator ILIKE '%Dokter%' THEN ind.nilai END), 0)::int as total_dokter
            FROM ref_wilayah w
            LEFT JOIN v_choropleth_wilayah c ON c.kode_bps = w.kode_bps
            LEFT JOIN tbl_indikator_kesehatan ind ON ind.kode_bps = w.kode_bps AND ind.topik = 'Tenaga Medis'
            WHERE w.kode_bps IN (:a, :b)
            GROUP BY w.kode_bps, w.nama_wilayah, w.tipe, c.total_rs, c.total_puskesmas, c.total_tt, c.jumlah_penduduk_2021, c.proyeksi_penduduk_2026, c.rasio_tt_resmi, c.rasio_tt_proyeksi_2026;
        """)
        res = await db.execute(query, {"a": kode_bps_a, "b": kode_bps_b})
        rows = {r["kode_bps"]: dict(r) for r in res.mappings().all()}

        data_a = rows.get(kode_bps_a, {})
        data_b = rows.get(kode_bps_b, {})

        diff = {
            "selisih_tt": (data_a.get("total_tt", 0) - data_b.get("total_tt", 0)),
            "selisih_dokter": (data_a.get("total_dokter", 0) - data_b.get("total_dokter", 0)),
            "selisih_rasio_2026": round(data_a.get("rasio_tt_proyeksi_2026", 0.0) - data_b.get("rasio_tt_proyeksi_2026", 0.0), 2),
        }

        return WilayahCompareResponse(
            wilayah_a=data_a,
            wilayah_b=data_b,
            comparison=diff,
        )
