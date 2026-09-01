import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from backend.app.models.wilayah import RefWilayah
from backend.app.schemas.wilayah import WilayahBase, WilayahDetail, WilayahAgregatSummary, ChoroplethWilayahItem
from backend.app.schemas.common import GeoJSONFeatureCollection, GeoJSONFeature, GeoJSONGeometry


def compute_who_category(ratio: float) -> str:
    if ratio >= 1.0:
        return "hijau"
    elif ratio >= 0.7:
        return "kuning"
    return "merah"


class WilayahService:
    @staticmethod
    async def get_all_wilayah(db: AsyncSession) -> List[WilayahBase]:
        stmt = select(RefWilayah).order_by(RefWilayah.kode_bps)
        result = await db.execute(stmt)
        wilayah_list = result.scalars().all()
        return [WilayahBase.model_validate(w) for w in wilayah_list]

    @staticmethod
    async def get_wilayah_detail(db: AsyncSession, kode_bps: str) -> Optional[WilayahDetail]:
        stmt = select(RefWilayah).where(RefWilayah.kode_bps == kode_bps)
        result = await db.execute(stmt)
        w = result.scalar_one_or_none()
        if not w:
            return None

        query_agg = text("""
            SELECT 
                total_rs,
                total_puskesmas,
                total_tt,
                jumlah_penduduk_2021,
                rasio_tt_resmi,
                kategori_who_resmi,
                proyeksi_penduduk_2026,
                rasio_tt_proyeksi_2026
            FROM v_choropleth_wilayah
            WHERE kode_bps = :kode_bps
        """)
        agg_res = await db.execute(query_agg, {"kode_bps": kode_bps})
        agg_row = agg_res.mappings().first()

        agregat_summary = None
        if agg_row:
            rasio_proj = float(agg_row["rasio_tt_proyeksi_2026"] or 0.0)
            agregat_summary = WilayahAgregatSummary(
                total_rs=int(agg_row["total_rs"] or 0),
                total_puskesmas=int(agg_row["total_puskesmas"] or 0),
                total_tt=int(agg_row["total_tt"] or 0),
                jumlah_penduduk_2021=int(agg_row["jumlah_penduduk_2021"] or 0),
                rasio_tt_resmi=float(agg_row["rasio_tt_resmi"] or 0.0),
                kategori_who_resmi=str(agg_row["kategori_who_resmi"] or "kuning"),
                proyeksi_penduduk_2026=int(agg_row["proyeksi_penduduk_2026"] or 0),
                rasio_tt_proyeksi_2026=rasio_proj,
                kategori_who_proyeksi_2026=compute_who_category(rasio_proj),
            )

        return WilayahDetail(
            kode_bps=w.kode_bps,
            nama_wilayah=w.nama_wilayah,
            tipe=w.tipe,
            agregat=agregat_summary,
        )

    @staticmethod
    async def get_choropleth_data(db: AsyncSession) -> List[ChoroplethWilayahItem]:
        query = text("""
            SELECT 
                kode_bps,
                nama_wilayah,
                tipe::text as tipe,
                total_rs,
                total_puskesmas,
                total_tt,
                jumlah_penduduk_2021,
                rasio_tt_resmi,
                kategori_who_resmi,
                proyeksi_penduduk_2026,
                rasio_tt_proyeksi_2026,
                ST_AsGeoJSON(geom) as geojson_str
            FROM v_choropleth_wilayah
            ORDER BY kode_bps
        """)
        result = await db.execute(query)
        rows = result.mappings().all()

        items: List[ChoroplethWilayahItem] = []
        for r in rows:
            geojson_obj = json.loads(r["geojson_str"]) if r["geojson_str"] else None
            rasio_proj = float(r["rasio_tt_proyeksi_2026"] or 0.0)
            items.append(
                ChoroplethWilayahItem(
                    kode_bps=r["kode_bps"],
                    nama_wilayah=r["nama_wilayah"],
                    tipe=r["tipe"],
                    total_rs=int(r["total_rs"] or 0),
                    total_puskesmas=int(r["total_puskesmas"] or 0),
                    total_tt=int(r["total_tt"] or 0),
                    jumlah_penduduk_2021=int(r["jumlah_penduduk_2021"] or 0),
                    rasio_tt_resmi=float(r["rasio_tt_resmi"] or 0.0),
                    kategori_who_resmi=str(r["kategori_who_resmi"] or "kuning"),
                    proyeksi_penduduk_2026=int(r["proyeksi_penduduk_2026"] or 0),
                    rasio_tt_proyeksi_2026=rasio_proj,
                    kategori_who_proyeksi_2026=compute_who_category(rasio_proj),
                    geojson=geojson_obj,
                )
            )
        return items

    @staticmethod
    async def get_choropleth_geojson(db: AsyncSession) -> GeoJSONFeatureCollection:
        items = await WilayahService.get_choropleth_data(db)
        features: List[GeoJSONFeature] = []

        for item in items:
            geom = None
            if item.geojson:
                geom = GeoJSONGeometry(
                    type=item.geojson.get("type", "MultiPolygon"),
                    coordinates=item.geojson.get("coordinates", []),
                )

            props = item.model_dump(exclude={"geojson"})
            features.append(GeoJSONFeature(type="Feature", geometry=geom, properties=props))

        return GeoJSONFeatureCollection(
            type="FeatureCollection",
            features=features,
            meta={"total_districts": len(features), "coverage_periode": "2026-PROJECTED"},
        )
