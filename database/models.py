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

class EnumTipeRawatPuskesmas(str, enum.Enum):
    rawat_inap = "rawat_inap"
    non_rawat_inap = "non_rawat_inap"

class EnumJenisNakes(str, enum.Enum):
    dokter_umum = "dokter_umum"
    dokter_spesialis = "dokter_spesialis"
    dokter_gigi = "dokter_gigi"
    perawat = "perawat"
    bidan = "bidan"
    ahli_gizi = "ahli_gizi"
    anestesi = "anestesi"
    sanitarian = "sanitarian"

class EnumTipePelayanan(str, enum.Enum):
    rawat_inap = "rawat_inap"
    rawat_jalan = "rawat_jalan"
    igd = "igd"

class EnumStatusKasusPenyakit(str, enum.Enum):
    menular = "menular"
    tidak_menular = "tidak_menular"

class EnumSurveillanceStatus(str, enum.Enum):
    normal = "normal"
    waspada = "waspada"
    perhatian = "perhatian"

class EnumAlertSeverity(str, enum.Enum):
    informasi = "informasi"
    waspada = "waspada"
    kritis = "kritis"

class EnumAlertStatus(str, enum.Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"

class EnumTipeWilayah(str, enum.Enum):
    KABUPATEN = "KABUPATEN"
    KOTA = "KOTA"

class EnumPipelineStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

class RefSumberData(Base):
    """Katalog sumber data resmi — sesuai SCHEMA.md Seksi 3 dan PRD v1.1 Seksi 9.3."""
    __tablename__ = "ref_sumber_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(50), unique=True, nullable=False, index=True)
    nama = Column(String(200), nullable=False)
    institusi = Column(String(200), nullable=True)
    url = Column(Text, nullable=True)
    lisensi = Column(String(200), nullable=True)
    lisensi_url = Column(Text, nullable=True)
    cakupan_wilayah = Column(String(100), nullable=True)
    cakupan_periode = Column(String(100), nullable=True)
    format_asli = Column(String(20), nullable=True)
    catatan_batasan = Column(Text, nullable=True)
    frekuensi_update = Column(String(50), nullable=True)  # daily, weekly, monthly, annual, once
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefIcd10(Base):
    """Master kode penyakit ICD-10 — sesuai SCHEMA.md Seksi 3."""
    __tablename__ = "ref_icd10"

    kode = Column(String(10), primary_key=True)  # e.g. 'A15', 'A90', 'J18'
    nama_en = Column(String(300), nullable=True)
    nama_id = Column(String(300), nullable=True)
    kategori = Column(String(100), nullable=True)  # e.g. 'Penyakit Infeksi'
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefWilayah(Base):
    __tablename__ = "ref_wilayah"

    kode_bps = Column(String(4), primary_key=True) # Contoh: '3578' Kota Surabaya
    nama_wilayah = Column(String(100), nullable=False)
    tipe = Column(Enum(EnumTipeWilayah, name="enum_tipe_wilayah"), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rumah_sakit = relationship("TblRumahSakit", back_populates="wilayah")
    puskesmas = relationship("FaskesPuskesmas", back_populates="wilayah")
    penduduk = relationship("TblPenduduk", back_populates="wilayah", uselist=False)
    indikator = relationship("TblIndikatorKesehatan", back_populates="wilayah")
    agregat = relationship("TblAgregatWilayah", back_populates="wilayah", uselist=False)
    nakes = relationship("TblTenagaKesehatan", back_populates="wilayah")
    morbiditas = relationship("TblPasienPenyakitWilayah", back_populates="wilayah")
    indikator_kia = relationship("IndikatorKia", back_populates="wilayah")
    surveillance = relationship("PenyakitSurveillance", back_populates="wilayah")
    alerts = relationship("AlertEvent", back_populates="wilayah")

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

class FaskesPuskesmas(Base):
    """
    Master Puskesmas di Jawa Timur — sesuai SCHEMA.md Seksi 4 dan PRD v1.1 Seksi 4.
    Mencakup faskes rawat inap dan non rawat inap per kecamatan/kabupaten.
    """
    __tablename__ = "faskes_puskesmas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_puskesmas = Column(String(50), unique=True, nullable=False, index=True)
    nama = Column(String(300), nullable=False)
    tipe_rawat = Column(
        Enum(EnumTipeRawatPuskesmas, name="enum_tipe_rawat_puskesmas"),
        default=EnumTipeRawatPuskesmas.non_rawat_inap,
        nullable=False,
        index=True
    )
    alamat = Column(Text, nullable=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="SET NULL"), nullable=True, index=True)
    kecamatan = Column(String(100), nullable=True)
    telepon = Column(String(100), nullable=True)
    jumlah_tt = Column(Integer, default=0)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geom = Column(Geometry("POINT", srid=4326), nullable=True)
    is_valid_coord = Column(Integer, default=1)
    needs_geocoding = Column(Integer, default=0)
    source_id = Column(String(50), default="opendata_jatim")
    status_operasional = Column(Integer, default=1)
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wilayah = relationship("RefWilayah", back_populates="puskesmas")


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

class TblTenagaKesehatan(Base):
    """
    Data SDM / Tenaga Kesehatan per Kabupaten/Kota — Domain B.
    Mendukung use-case ML Disparity Clustering & Doctor-Patient Ratio Analysis.
    """
    __tablename__ = "tbl_tenaga_kesehatan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, default=2024, index=True)
    semester = Column(Integer, default=1)
    jenis_nakes = Column(Enum(EnumJenisNakes, name="enum_jenis_nakes"), nullable=False, index=True)
    jumlah = Column(Integer, nullable=False, default=0)
    faskes_level = Column(String(50), default="Semua Faskes")
    sumber_data = Column(String(100), default="Dinas Kesehatan Provinsi Jawa Timur")
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "semester", "jenis_nakes", "faskes_level", name="uq_nakes_wilayah_tahun"),
    )

    wilayah = relationship("RefWilayah", back_populates="nakes")


class TblPasienPenyakitWilayah(Base):
    """
    Trend Morbiditas Pasien dan Kasus Penyakit per Wilayah — Domain C.
    Mendukung use-case ML Patient Inflow Forecasting & Outbreak Risk Classifier.
    """
    __tablename__ = "tbl_pasien_penyakit_wilayah"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, default=2024, index=True)
    triwulan = Column(String(10), nullable=False, default="Q1")  # Q1, Q2, Q3, Q4, TAHUNAN
    tipe_pelayanan = Column(Enum(EnumTipePelayanan, name="enum_tipe_pelayanan"), default=EnumTipePelayanan.rawat_inap, index=True)
    nama_penyakit = Column(String(200), nullable=False, index=True)
    kode_icd10 = Column(String(10), nullable=True, index=True)
    jumlah_pasien = Column(Integer, nullable=False, default=0)
    status_kasus = Column(Enum(EnumStatusKasusPenyakit, name="enum_status_kasus_penyakit"), default=EnumStatusKasusPenyakit.menular)
    sumber_data = Column(String(100), default="Dinas Kesehatan Provinsi Jawa Timur")
    coverage_periode = Column(String(20), default="2024-OFFICIAL")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "triwulan", "tipe_pelayanan", "nama_penyakit", name="uq_morbiditas_wilayah"),
    )

    wilayah = relationship("RefWilayah", back_populates="morbiditas")


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


class IndikatorKia(Base):
    """
    Sub-domain Kesehatan Ibu & Anak (KIA) — sesuai SCHEMA.md Seksi 7 dan PRD v3.0 F-PP03.
    """
    __tablename__ = "indikator_kia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    tahun = Column(Integer, nullable=False, index=True)
    bulan = Column(Integer, nullable=True)  # NULL = tahunan, 1-12 = bulanan

    # Kematian Ibu & Bayi
    aki = Column(Float, nullable=True)  # per 100.000 KH
    akb = Column(Float, nullable=True)  # per 1.000 KH
    akaba = Column(Float, nullable=True)  # per 1.000 KH
    jumlah_kelahiran_hidup = Column(Integer, nullable=True)
    jumlah_kematian_ibu = Column(Integer, nullable=True)
    jumlah_kematian_bayi = Column(Integer, nullable=True)

    # Antenatal & Persalinan
    k1_coverage = Column(Float, nullable=True)
    k4_coverage = Column(Float, nullable=True)
    persen_persalinan_faskes = Column(Float, nullable=True)
    persen_bblr = Column(Float, nullable=True)

    # Gizi & Stunting
    prevalensi_stunting = Column(Float, nullable=True)
    prevalensi_gizi_buruk = Column(Float, nullable=True)
    prevalensi_gizi_kurang = Column(Float, nullable=True)
    prevalensi_gizi_lebih = Column(Float, nullable=True)
    ds_ratio_posyandu = Column(Float, nullable=True)

    # Imunisasi
    cakupan_idl = Column(Float, nullable=True)
    persen_desa_uci = Column(Float, nullable=True)
    dropout_rate_imunisasi = Column(Float, nullable=True)

    source_id = Column(String(50), ForeignKey("ref_sumber_data.source_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "tahun", "bulan", name="uq_kia_wilayah_waktu"),
    )

    wilayah = relationship("RefWilayah", back_populates="indikator_kia")


class PenyakitSurveillance(Base):
    """
    Kalkulasi Surveillance Cepat Mingguan/Bulanan Potensial KLB — SCHEMA.md Seksi 6 & PRD F-PP05.
    """
    __tablename__ = "penyakit_surveillance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    kode_icd10 = Column(String(10), ForeignKey("ref_icd10.kode"), nullable=True, index=True)
    periode_bulan = Column(String(10), nullable=False, index=True)  # YYYY-MM

    kasus_bulan_ini = Column(Integer, nullable=False, default=0)
    rata_rata_3bln = Column(Float, nullable=False, default=0.0)
    delta_persen = Column(Float, nullable=False, default=0.0)
    status_surveillance = Column(Enum(EnumSurveillanceStatus, name="enum_surveillance_status"), default=EnumSurveillanceStatus.normal, index=True)

    calculated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("kode_bps", "kode_icd10", "periode_bulan", name="uq_surveillance_wilayah_periode"),
    )

    wilayah = relationship("RefWilayah", back_populates="surveillance")


class AlertRule(Base):
    """
    Master Rule Deteksi Anomali / Ambang Batas Early Warning — SCHEMA.md Seksi 10 & PRD F-EW01.
    """
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kode = Column(String(50), unique=True, nullable=False, index=True)
    nama = Column(String(200), nullable=False)
    blok = Column(String(20), nullable=False)  # fasilitas, nakes, penyakit, kia, stok_obat
    kondisi_desc = Column(Text, nullable=True)
    threshold = Column(JSON, nullable=False)  # e.g. {"metrik": "bor", "operator": ">", "nilai": 85}
    severity = Column(Enum(EnumAlertSeverity, name="enum_alert_severity"), default=EnumAlertSeverity.waspada)
    rekomendasi = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("AlertEvent", back_populates="rule")


class AlertEvent(Base):
    """
    Log Insiden Alert yang Terpicu — SCHEMA.md Seksi 10 & PRD F-EW02.
    """
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    kode_bps = Column(String(4), ForeignKey("ref_wilayah.kode_bps", ondelete="CASCADE"), nullable=False, index=True)
    faskes_id = Column(Integer, nullable=True)  # Optional ID RS/Puskesmas
    faskes_tipe = Column(String(20), nullable=True)
    nilai_terdeteksi = Column(Float, nullable=False)
    pesan = Column(Text, nullable=False)
    severity = Column(Enum(EnumAlertSeverity, name="enum_alert_severity"), default=EnumAlertSeverity.waspada)
    status = Column(Enum(EnumAlertStatus, name="enum_alert_status"), default=EnumAlertStatus.active, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    rule = relationship("AlertRule", back_populates="events")
    wilayah = relationship("RefWilayah", back_populates="alerts")

