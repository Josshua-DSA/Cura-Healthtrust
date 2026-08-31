import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index, Enum, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

Base = declarative_base()

class EnumKelasRS(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    tidak_diketahui = "tidak_diketahui"

class EnumKepemilikan(str, enum.Enum):
    pemerintah = "pemerintah"
    swasta = "swasta"
    tni_polri = "tni_polri"
    lainnya = "lainnya"

class EnumTipeWilayah(str, enum.Enum):
    KABUPATEN = "KABUPATEN"
    KOTA = "KOTA"

class EnumPipelineStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

class RefWilayah(Base):
    __tablename__ = "ref_wilayah"

    kode_bps = Column(String(4), primary_key=True) # Contoh: '3578' Kota Surabaya
    nama_wilayah = Column(String(100), nullable=False)
    tipe = Column(Enum(EnumTipeWilayah, name="enum_tipe_wilayah"), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rumah_sakit = relationship("TblRumahSakit", back_populates="wilayah")
    penduduk = relationship("TblPenduduk", back_populates="wilayah")
    agregat = relationship("TblAgregatWilayah", back_populates="wilayah")
    indikator = relationship("TblIndikatorKesehatan", back_populates="wilayah")

class TblIndikatorKesehatan(Base):
    __tablename__ = "tbl_indikator_kesehatan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    topik = Column(String(100), nullable=False, index=True) # Puskesmas, Tenaga Medis, KIA, Gizi, dll
    nama_indikator = Column(String(255), nullable=False) # e.g. 'Jumlah Puskesmas Rawat Inap'
    nilai = Column(Float, nullable=False)
    satuan = Column(String(50), nullable=True)
    sumber_data = Column(String(100), default="Dinas Kesehatan Provinsi Jawa Timur")
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "nama_indikator", name="uq_indikator_wilayah_tahun"),
        Index("idx_indikator_topik_tahun", "topik", "tahun")
    )

    wilayah = relationship("RefWilayah", back_populates="indikator")

class TblPenduduk(Base):
    __tablename__ = "tbl_penduduk"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False)
    tahun = Column(Integer, nullable=False)
    jumlah_penduduk = Column(Integer, nullable=False)
    sumber = Column(String(100), default="BPS Jawa Timur")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", name="uq_wilayah_tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="penduduk")

class TblRumahSakit(Base):
    __tablename__ = "tbl_rumah_sakit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_rs = Column(String(50), unique=True, nullable=False, index=True) # Kode SIRS atau hash
    nama_rs = Column(String(255), nullable=False)
    alamat = Column(Text, nullable=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="SET NULL"), nullable=True, index=True)
    kelas = Column(Enum(EnumKelasRS, name="enum_kelas_rs"), default=EnumKelasRS.tidak_diketahui, index=True)
    kepemilikan = Column(Enum(EnumKepemilikan, name="enum_kepemilikan"), default=EnumKepemilikan.lainnya, index=True)
    pemilik_raw = Column(String(50), nullable=True)  # Nilai mentah SIRS sebelum mapping enum
    jenis_rs = Column(String(50), default="RSU")
    jumlah_tt = Column(Integer, default=0)
    layanan = Column(JSON, default=list) # ['ICU', 'IGD', 'Rawat Inap', ...]
    telepon = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    is_valid_coord = Column(Integer, default=1)  # 1=valid, 0=dummy/OOB/null
    needs_geocoding = Column(Integer, default=0)  # 1=perlu geocode ulang
    sumber_data = Column(String(100), nullable=False)
    coverage_periode = Column(String(20), default="2026-LIVE")
    last_updated_source = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wilayah = relationship("RefWilayah", back_populates="rumah_sakit")

class TblAgregatWilayah(Base):
    __tablename__ = "tbl_agregat_wilayah"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False)
    tahun = Column(Integer, nullable=False)
    total_rs = Column(Integer, default=0, nullable=False)
    total_tt = Column(Integer, default=0, nullable=False)
    jumlah_penduduk = Column(Integer, default=0, nullable=False)
    rasio_tt_per_1000 = Column(Float, default=0.0, nullable=False)
    kategori_ketercukupan = Column(String(20), default="kuning") # hijau, kuning, merah
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", name="uq_agregat_wilayah_tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="agregat")

class TblPipelineLog(Base):
    __tablename__ = "tbl_pipeline_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(50), nullable=False)
    run_started_at = Column(DateTime, nullable=False)
    run_finished_at = Column(DateTime, nullable=True)
    record_extracted = Column(Integer, default=0)
    record_loaded = Column(Integer, default=0)
    status = Column(Enum(EnumPipelineStatus, name="enum_pipeline_status"), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
