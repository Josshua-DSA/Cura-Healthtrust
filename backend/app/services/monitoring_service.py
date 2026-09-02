import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.app.repositories.monitoring_repository import KiaRepository, AlertRepository
from backend.app.schemas.monitoring import (
    IndikatorKiaItem,
    KiaSummary,
    AlertRuleItem,
    AlertEventItem,
)
from backend.app.schemas.common import (
    GeoJSONFeatureCollection,
    GeoJSONFeature,
    GeoJSONGeometry,
)


class KiaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = KiaRepository(db)

    async def get_kia_summary(self) -> KiaSummary:
        query = text("""
            SELECT 
                COUNT(*) as total_wilayah,
                ROUND(AVG(prevalensi_stunting)::numeric, 2) as avg_stunting,
                ROUND(AVG(aki)::numeric, 2) as avg_aki,
                ROUND(AVG(akb)::numeric, 2) as avg_akb,
                ROUND(AVG(cakupan_idl)::numeric, 2) as avg_imunisasi
            FROM indikator_kia
            WHERE bulan IS NULL;
        """)
        res = await self.db.execute(query)
        row = res.mappings().first()

        # Highest & Lowest Stunting
        q_high = text("""
            SELECT w.nama_wilayah, k.prevalensi_stunting
            FROM indikator_kia k
            JOIN ref_wilayah w ON w.kode_bps = k.kode_bps
            ORDER BY k.prevalensi_stunting DESC
            LIMIT 1;
        """)
        r_high = (await self.db.execute(q_high)).mappings().first()

        q_low = text("""
            SELECT w.nama_wilayah, k.prevalensi_stunting
            FROM indikator_kia k
            JOIN ref_wilayah w ON w.kode_bps = k.kode_bps
            ORDER BY k.prevalensi_stunting ASC
            LIMIT 1;
        """)
        r_low = (await self.db.execute(q_low)).mappings().first()

        return KiaSummary(
            total_wilayah=int(row["total_wilayah"] or 38),
            avg_stunting=float(row["avg_stunting"] or 0.0),
            avg_aki=float(row["avg_aki"] or 0.0),
            avg_akb=float(row["avg_akb"] or 0.0),
            avg_cakupan_imunisasi=float(row["avg_imunisasi"] or 0.0),
            highest_stunting_wilayah=f"{r_high['nama_wilayah']} ({r_high['prevalensi_stunting']}%)" if r_high else None,
            lowest_stunting_wilayah=f"{r_low['nama_wilayah']} ({r_low['prevalensi_stunting']}%)" if r_low else None,
        )

    async def get_kia_by_wilayah(self, kode_bps: str) -> Optional[IndikatorKiaItem]:
        rec = await self.repo.get_by_wilayah(kode_bps)
        if not rec:
            return None
        item = IndikatorKiaItem.model_validate(rec)
        if rec.wilayah:
            item.nama_wilayah = rec.wilayah.nama_wilayah
        return item

    async def get_kia_choropleth(self, metrik: str = "stunting") -> GeoJSONFeatureCollection:
        # Metrik valid: stunting, aki, akb, cakupan_idl
        col = "prevalensi_stunting"
        if metrik == "aki":
            col = "aki"
        elif metrik == "akb":
            col = "akb"
        elif metrik == "imunisasi":
            col = "cakupan_idl"

        query = text(f"""
            SELECT 
                w.kode_bps,
                w.nama_wilayah,
                k.{col} as nilai_metrik,
                ST_AsGeoJSON(w.geom) as geojson
            FROM ref_wilayah w
            LEFT JOIN indikator_kia k ON k.kode_bps = w.kode_bps
            WHERE w.geom IS NOT NULL
            ORDER BY w.kode_bps;
        """)
        res = await self.db.execute(query)
        features: List[GeoJSONFeature] = []

        for row in res.mappings().all():
            geom_dict = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom_dict:
                continue

            feature = GeoJSONFeature(
                geometry=GeoJSONGeometry(type=geom_dict["type"], coordinates=geom_dict["coordinates"]),
                properties={
                    "kode_bps": row["kode_bps"],
                    "nama_wilayah": row["nama_wilayah"],
                    "metrik": metrik,
                    "nilai": float(row["nilai_metrik"] or 0.0),
                },
            )
            features.append(feature)

        return GeoJSONFeatureCollection(features=features)


class DecisionAlertService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AlertRepository(db)

    async def get_rules(self) -> List[AlertRuleItem]:
        rules = await self.repo.list_active_rules()
        return [AlertRuleItem.model_validate(r) for r in rules]

    async def get_events(self, status: Optional[str] = None, severity: Optional[str] = None) -> List[AlertEventItem]:
        events = await self.repo.list_events(status=status, severity=severity)
        items: List[AlertEventItem] = []
        for e in events:
            item = AlertEventItem.model_validate(e)
            if e.rule:
                item.nama_rule = e.rule.nama
            if e.wilayah:
                item.nama_wilayah = e.wilayah.nama_wilayah
            if e.triggered_at:
                item.triggered_at = e.triggered_at.isoformat()
            if e.resolved_at:
                item.resolved_at = e.resolved_at.isoformat()
            items.append(item)
        return items
