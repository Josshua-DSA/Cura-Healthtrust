from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from backend.app.core.database import Base
from backend.app.models.enums import EnumKelasRS, EnumKepemilikan, EnumTipeRawatPuskesmas


class TblRumahSakit(Base):
    __tablename__ = "tbl_rumah_sakit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_rs = Column(String(50), unique=True, nullable=False, index=True)
    nama_rs = Column(String(255), nullable=False, index=True)
    alamat = Column(Text, nullable=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="SET NULL"), nullable=True, index=True)
    kelas = Column(Enum(EnumKelasRS, name="enum_kelas_rs"), default=EnumKelasRS.tidak_diketahui, index=True)
    kepemilikan = Column(Enum(EnumKepemilikan, name="enum_kepemilikan"), default=EnumKepemilikan.lainnya, index=True)
    pemilik_raw = Column(String(50), nullable=True)
    jenis_rs = Column(String(50), default="RSU")
    jumlah_tt = Column(Integer, default=0)
    layanan = Column(JSON, default=list)
    telepon = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    is_valid_coord = Column(Integer, default=1)
    needs_geocoding = Column(Integer, default=0)
    sumber_data = Column(String(100), nullable=False, default="SIRS Kemenkes")
    coverage_periode = Column(String(20), default="2026-LIVE")
    last_updated_source = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wilayah = relationship("RefWilayah", back_populates="rumah_sakit", lazy="selectin")


class FaskesPuskesmas(Base):
    __tablename__ = "faskes_puskesmas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_puskesmas = Column(String(50), unique=True, nullable=False, index=True)
    nama = Column(String(255), nullable=False, index=True)
    tipe_rawat = Column(
        Enum(EnumTipeRawatPuskesmas, name="enum_tipe_rawat_puskesmas"),
        default=EnumTipeRawatPuskesmas.non_rawat_inap,
        nullable=False,
        index=True
    )
    alamat = Column(Text, nullable=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="SET NULL"), nullable=True, index=True)
    kecamatan = Column(String(100), nullable=True)
    telepon = Column(String(50), nullable=True)
    jumlah_tt = Column(Integer, default=0)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    is_valid_coord = Column(Integer, default=1)
    needs_geocoding = Column(Integer, default=0)
    source_id = Column(String(50), ForeignKey("ref_sumber_data.source_id", ondelete="SET NULL"), nullable=True)
    status_operasional = Column(Integer, default=1)
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wilayah = relationship("RefWilayah", back_populates="puskesmas", lazy="selectin")
