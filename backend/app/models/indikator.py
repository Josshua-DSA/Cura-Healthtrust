from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class TblIndikatorKesehatan(Base):
    __tablename__ = "tbl_indikator_kesehatan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    topik = Column(String(100), nullable=False, index=True)
    nama_indikator = Column(String(255), nullable=False)
    nilai = Column(Float, nullable=False)
    satuan = Column(String(50), nullable=True)
    sumber_file = Column(String(255), nullable=True)
    sumber_data = Column(String(100), default="Dinas Kesehatan Provinsi Jawa Timur")
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "nama_indikator", name="uq_indikator_wilayah_tahun"),
        Index("idx_indikator_topik_tahun", "topik", "tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="indikator", lazy="selectin")


class TblPenduduk(Base):
    __tablename__ = "tbl_penduduk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    jumlah_penduduk = Column(Integer, nullable=False)
    sumber = Column(String(100), default="BPS Jawa Timur")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", name="uq_wilayah_tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="penduduk", lazy="selectin")


class TblAgregatWilayah(Base):
    __tablename__ = "tbl_agregat_wilayah"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    total_rs = Column(Integer, default=0, nullable=False)
    total_tt = Column(Integer, default=0, nullable=False)
    jumlah_penduduk = Column(Integer, default=0, nullable=False)
    rasio_tt_per_1000 = Column(Float, default=0.0, nullable=False)
    kategori_ketercukupan = Column(String(20), default="kuning")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", name="uq_agregat_wilayah_tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="agregat", lazy="selectin")
