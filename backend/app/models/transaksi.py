from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, 
    UniqueConstraint, Index, Enum
)
from sqlalchemy.orm import relationship
import enum

from backend.app.core.database import Base


class EnumJenisKunjungan(str, enum.Enum):
    rawat_jalan = "rawat_jalan"
    rawat_inap = "rawat_inap"
    igd = "igd"


class TrxKunjungan(Base):
    __tablename__ = "trx_kunjungan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    faskes_id = Column(String(50), nullable=False, index=True)  # kode_rs atau kode_puskesmas
    tanggal = Column(Date, nullable=False, index=True)
    jenis_kunjungan = Column(
        Enum(EnumJenisKunjungan, name="enum_jenis_kunjungan"),
        default=EnumJenisKunjungan.rawat_jalan,
        nullable=False,
        index=True
    )
    poli = Column(String(100), nullable=True)
    jumlah_pasien = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_trx_kunjungan_faskes_tgl", "faskes_id", "tanggal"),
    )


class TrxOccupancy(Base):
    __tablename__ = "trx_occupancy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    faskes_id = Column(String(50), nullable=False, index=True)
    periode = Column(String(7), nullable=False, index=True)  # Format 'YYYY-MM' e.g. '2026-08'
    bor = Column(Float, nullable=False)  # Bed Occupancy Rate (%)
    alos = Column(Float, nullable=True)  # Average Length of Stay (days)
    toi = Column(Float, nullable=True)   # Turn Over Interval (days)
    bto = Column(Float, nullable=True)   # Bed Turn Over (times)
    total_tempat_tidur = Column(Integer, nullable=False)
    hari_perawatan = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("faskes_id", "periode", name="uq_trx_occupancy_faskes_periode"),
    )


class TrxStokObat(Base):
    __tablename__ = "trx_stok_obat"

    id = Column(Integer, primary_key=True, autoincrement=True)
    faskes_id = Column(String(50), nullable=False, index=True)
    kode_obat = Column(String(50), nullable=False, index=True)
    nama_obat = Column(String(200), nullable=False)
    satuan = Column(String(50), default="tablet")
    stok_tersedia = Column(Integer, default=0, nullable=False)
    stok_minimum = Column(Integer, default=100, nullable=False)
    pemakaian_bulanan = Column(Integer, default=0, nullable=False)
    status_stok = Column(String(20), default="aman")  # 'aman', 'waspada', 'kritis'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("faskes_id", "kode_obat", name="uq_trx_stok_faskes_obat"),
    )
