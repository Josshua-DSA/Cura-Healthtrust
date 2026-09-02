from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index, JSON, Text
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class IndikatorKia(Base):
    __tablename__ = "indikator_kia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    bulan = Column(Integer, nullable=True, index=True)  # NULL untuk data agregat tahunan
    aki = Column(Float, nullable=True)  # Angka Kematian Ibu per 100k KH
    akb = Column(Float, nullable=True)  # Angka Kematian Bayi per 1k KH
    akaba = Column(Float, nullable=True)  # Angka Kematian Balita
    jumlah_kelahiran_hidup = Column(Integer, nullable=True)
    jumlah_kematian_ibu = Column(Integer, nullable=True)
    jumlah_kematian_bayi = Column(Integer, nullable=True)
    k1_coverage = Column(Float, nullable=True)
    k4_coverage = Column(Float, nullable=True)
    persen_persalinan_faskes = Column(Float, nullable=True)
    persen_bblr = Column(Float, nullable=True)
    prevalensi_stunting = Column(Float, nullable=True)  # Persen stunting balita
    prevalensi_gizi_buruk = Column(Float, nullable=True)
    prevalensi_gizi_kurang = Column(Float, nullable=True)
    prevalensi_gizi_lebih = Column(Float, nullable=True)
    ds_ratio_posyandu = Column(Float, nullable=True)
    cakupan_idl = Column(Float, nullable=True)  # Imunisasi Dasar Lengkap
    persen_desa_uci = Column(Float, nullable=True)
    dropout_rate_imunisasi = Column(Float, nullable=True)
    source_id = Column(String(50), default="opendata_jatim")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wilayah = relationship("RefWilayah", lazy="selectin")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(50), unique=True, nullable=False)
    nama = Column(String(255), nullable=False)
    blok = Column(String(50), nullable=False)  # fasilitas, nakes, penyakit, early_warning
    kondisi_desc = Column(Text, nullable=True)
    threshold = Column(JSON, nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    rekomendasi = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="SET NULL"), nullable=True)
    faskes_id = Column(Integer, nullable=True)
    faskes_tipe = Column(String(20), nullable=True)  # RS, Puskesmas
    nilai_terdeteksi = Column(Float, nullable=True)
    pesan = Column(Text, nullable=False)
    severity = Column(String(20), default="medium")
    status = Column(String(20), default="open")  # open, acknowledged, resolved
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    rule = relationship("AlertRule", lazy="selectin")
    wilayah = relationship("RefWilayah", lazy="selectin")
