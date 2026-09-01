from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_, func

from backend.app.models.faskes import TblRumahSakit, FaskesPuskesmas
from backend.app.models.wilayah import RefWilayah
from backend.app.schemas.faskes import (
    FaskesBase,
    RumahSakitDetail,
    PuskesmasDetail,
    FaskesNearbyItem,
)
from backend.app.schemas.common import (
    PaginationMeta,
    PaginatedResponse,
    GeoJSONFeatureCollection,
    GeoJSONFeature,
    GeoJSONGeometry,
)


class FaskesService:
    @staticmethod
    async def get_faskes_list(
        db: AsyncSession,
        jenis_faskes: Optional[str] = None,  # 'rumah_sakit' | 'puskesmas'
        kode_bps: Optional[str] = None,
        kelas_rs: Optional[str] = None,
        kepemilikan: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[FaskesBase], int]:
        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"limit": page_size, "offset": offset}

        if jenis_faskes:
            where_clauses.append("jenis_faskes = :jenis_faskes")
            params["jenis_faskes"] = jenis_faskes

        if kode_bps:
            where_clauses.append("kode_bps = :kode_bps")
            params["kode_bps"] = kode_bps

        if kelas_rs:
            where_clauses.append("kelas_tipe = :kelas_rs")
            params["kelas_rs"] = kelas_rs

        if kepemilikan:
            where_clauses.append("kepemilikan = :kepemilikan")
            params["kepemilikan"] = kepemilikan

        if search:
            where_clauses.append("(nama ILIKE :search OR alamat ILIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses)

        count_query = text(f"SELECT COUNT(*) FROM v_faskes_all WHERE {where_sql}")
        total_records = await db.scalar(count_query, params) or 0

        data_query = text(f"""
            SELECT 
                id_faskes,
                jenis_faskes,
                nama,
                kelas_tipe,
                kepemilikan,
                alamat,
                kode_bps,
                telepon,
                jumlah_tt,
                lat,
                lng,
                is_valid_coord,
                coverage_periode
            FROM v_faskes_all
            WHERE {where_sql}
            ORDER BY jenis_faskes, nama
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(data_query, params)
        rows = result.mappings().all()

        items = [
            FaskesBase(
                id_faskes=r["id_faskes"],
                jenis_faskes=r["jenis_faskes"],
                nama=r["nama"],
                kelas_tipe=r["kelas_tipe"],
                kepemilikan=r["kepemilikan"],
                alamat=r["alamat"],
                kode_bps=r["kode_bps"],
                telepon=r["telepon"],
                jumlah_tt=int(r["jumlah_tt"] or 0),
                lat=r["lat"],
                lng=r["lng"],
                is_valid_coord=int(r["is_valid_coord"] or 0),
                coverage_periode=r["coverage_periode"] or "2026-LIVE",
            )
            for r in rows
        ]

        return items, int(total_records)

    @staticmethod
    async def get_hospital_detail(db: AsyncSession, kode_rs: str) -> Optional[RumahSakitDetail]:
        stmt = (
            select(TblRumahSakit, RefWilayah.nama_wilayah)
            .outerjoin(RefWilayah, TblRumahSakit.kode_bps == RefWilayah.kode_bps)
            .where(TblRumahSakit.kode_rs == kode_rs)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None

        rs, nama_wilayah = row
        return RumahSakitDetail(
            id=rs.id,
            kode_rs=rs.kode_rs,
            nama_rs=rs.nama_rs,
            alamat=rs.alamat,
            kode_bps=rs.kode_bps,
            nama_wilayah=nama_wilayah,
            kelas=rs.kelas,
            kepemilikan=rs.kepemilikan,
            pemilik_raw=rs.pemilik_raw,
            jenis_rs=rs.jenis_rs,
            jumlah_tt=rs.jumlah_tt or 0,
            layanan=rs.layanan or [],
            telepon=rs.telepon,
            website=rs.website,
            lat=rs.lat,
            lng=rs.lng,
            is_valid_coord=rs.is_valid_coord,
            sumber_data=rs.sumber_data,
            coverage_periode=rs.coverage_periode,
        )

    @staticmethod
    async def get_puskesmas_detail(db: AsyncSession, kode_puskesmas: str) -> Optional[PuskesmasDetail]:
        stmt = (
            select(FaskesPuskesmas, RefWilayah.nama_wilayah)
            .outerjoin(RefWilayah, FaskesPuskesmas.kode_bps == RefWilayah.kode_bps)
            .where(FaskesPuskesmas.kode_puskesmas == kode_puskesmas)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None

        pkm, nama_wilayah = row
        return PuskesmasDetail(
            id=pkm.id,
            kode_puskesmas=pkm.kode_puskesmas,
            nama=pkm.nama,
            tipe_rawat=pkm.tipe_rawat,
            alamat=pkm.alamat,
            kode_bps=pkm.kode_bps,
            nama_wilayah=nama_wilayah,
            kecamatan=pkm.kecamatan,
            telepon=pkm.telepon,
            jumlah_tt=pkm.jumlah_tt or 0,
            lat=pkm.lat,
            lng=pkm.lng,
            is_valid_coord=pkm.is_valid_coord,
            source_id=pkm.source_id,
            coverage_periode=pkm.coverage_periode,
        )

    @staticmethod
    async def get_faskes_geojson(
        db: AsyncSession,
        jenis_faskes: Optional[str] = None,
        kode_bps: Optional[str] = None,
    ) -> GeoJSONFeatureCollection:
        where_clauses = ["is_valid_coord = 1", "lat IS NOT NULL", "lng IS NOT NULL"]
        params: Dict[str, Any] = {}

        if jenis_faskes:
            where_clauses.append("jenis_faskes = :jenis_faskes")
            params["jenis_faskes"] = jenis_faskes

        if kode_bps:
            where_clauses.append("kode_bps = :kode_bps")
            params["kode_bps"] = kode_bps

        where_sql = " AND ".join(where_clauses)

        query = text(f"""
            SELECT 
                id_faskes,
                jenis_faskes,
                nama,
                kelas_tipe,
                kepemilikan,
                alamat,
                kode_bps,
                telepon,
                jumlah_tt,
                lat,
                lng,
                coverage_periode
            FROM v_faskes_all
            WHERE {where_sql}
        """)
        result = await db.execute(query, params)
        rows = result.mappings().all()

        features: List[GeoJSONFeature] = []
        for r in rows:
            geom = GeoJSONGeometry(
                type="Point",
                coordinates=[r["lng"], r["lat"]],
            )
            props = {
                "id_faskes": r["id_faskes"],
                "jenis_faskes": r["jenis_faskes"],
                "nama": r["nama"],
                "kelas_tipe": r["kelas_tipe"],
                "kepemilikan": r["kepemilikan"],
                "alamat": r["alamat"],
                "kode_bps": r["kode_bps"],
                "telepon": r["telepon"],
                "jumlah_tt": int(r["jumlah_tt"] or 0),
                "coverage_periode": r["coverage_periode"],
            }
            features.append(GeoJSONFeature(type="Feature", geometry=geom, properties=props))

        return GeoJSONFeatureCollection(
            type="FeatureCollection",
            features=features,
            meta={"total_points": len(features)},
        )

    @staticmethod
    async def get_nearby_faskes(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius_km: float = 5.0,
        jenis_faskes: Optional[str] = None,
        limit: int = 20,
    ) -> List[FaskesNearbyItem]:
        """
        Sub-10ms Spatial Radius Query using PostGIS ST_DWithin & ST_Distance on geography point.
        """
        radius_meters = radius_km * 1000.0
        where_clauses = [
            "is_valid_coord = 1",
            "geom IS NOT NULL",
            "ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_meters)",
        ]
        params: Dict[str, Any] = {
            "lat": lat,
            "lng": lng,
            "radius_meters": radius_meters,
            "limit": limit,
        }

        if jenis_faskes:
            where_clauses.append("jenis_faskes = :jenis_faskes")
            params["jenis_faskes"] = jenis_faskes

        where_sql = " AND ".join(where_clauses)

        query = text(f"""
            SELECT 
                id_faskes,
                jenis_faskes,
                nama,
                kelas_tipe,
                kepemilikan,
                alamat,
                kode_bps,
                telepon,
                jumlah_tt,
                lat,
                lng,
                is_valid_coord,
                coverage_periode,
                ROUND(ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)::numeric, 1) as distance_meters
            FROM v_faskes_all
            WHERE {where_sql}
            ORDER BY distance_meters ASC
            LIMIT :limit
        """)

        result = await db.execute(query, params)
        rows = result.mappings().all()

        items: List[FaskesNearbyItem] = []
        for r in rows:
            dist_m = float(r["distance_meters"] or 0.0)
            items.append(
                FaskesNearbyItem(
                    id_faskes=r["id_faskes"],
                    jenis_faskes=r["jenis_faskes"],
                    nama=r["nama"],
                    kelas_tipe=r["kelas_tipe"],
                    kepemilikan=r["kepemilikan"],
                    alamat=r["alamat"],
                    kode_bps=r["kode_bps"],
                    telepon=r["telepon"],
                    jumlah_tt=int(r["jumlah_tt"] or 0),
                    lat=r["lat"],
                    lng=r["lng"],
                    is_valid_coord=int(r["is_valid_coord"] or 0),
                    coverage_periode=r["coverage_periode"] or "2026-LIVE",
                    distance_meters=dist_m,
                    distance_km=round(dist_m / 1000.0, 2),
                )
            )
        return items
