from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class TblTenagaKesehatan(Base):
    __tablename__ = "tbl_tenaga_kesehatan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    semester = Column(Integer, default=1)  # 1 atau 2
    jenis_nakes = Column(String(50), nullable=False, index=True)
    jumlah = Column(Integer, default=0, nullable=False)
    faskes_level = Column(String(50), default="Puskesmas", nullable=False, index=True)
    sumber_data = Column(String(100), default="Dinas Kesehatan Provinsi Jawa Timur")
    coverage_periode = Column(String(20), default="2025-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "semester", "jenis_nakes", "faskes_level", name="uq_nakes_wilayah_periode"),
        Index("idx_nakes_jenis_tahun", "jenis_nakes", "tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="tenaga_kesehatan", lazy="selectin")


class TblPasienPenyakitWilayah(Base):
    __tablename__ = "tbl_pasien_penyakit_wilayah"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    triwulan = Column(String(5), nullable=False, index=True)  # 'Q1', 'Q2', 'Q3', 'Q4'
    tipe_pelayanan = Column(String(50), default="rawat_jalan", nullable=False, index=True)
    nama_penyakit = Column(String(255), nullable=False, index=True)
    kode_icd10 = Column(String(10), ForeignKey("ref_icd10.kode", ondelete="SET NULL"), nullable=True, index=True)
    jumlah_pasien = Column(Integer, default=0, nullable=False)
    status_kasus = Column(String(50), default="tidak_menular", nullable=False, index=True)
    sumber_data = Column(String(100), default="Dinkes & OpenData Jatim")
    coverage_periode = Column(String(20), default="2025-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "triwulan", "tipe_pelayanan", "nama_penyakit", name="uq_penyakit_wilayah_periode"),
        Index("idx_penyakit_icd10_tahun", "kode_icd10", "tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="pasien_penyakit", lazy="selectin")
    icd10 = relationship("RefICD10", lazy="selectin")
