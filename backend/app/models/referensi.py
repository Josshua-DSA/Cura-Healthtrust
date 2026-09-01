from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum

from backend.app.core.database import Base
from backend.app.models.enums import EnumPipelineStatus


class RefSumberData(Base):
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
    frekuensi_update = Column(String(50), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefICD10(Base):
    __tablename__ = "ref_icd10"

    kode = Column(String(10), primary_key=True)
    nama_en = Column(String(300), nullable=True)
    nama_id = Column(String(300), nullable=True)
    kategori = Column(String(100), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class TblPipelineLog(Base):
    __tablename__ = "tbl_pipeline_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(50), nullable=False, index=True)
    run_started_at = Column(DateTime, nullable=False)
    run_finished_at = Column(DateTime, nullable=True)
    record_extracted = Column(Integer, default=0)
    record_loaded = Column(Integer, default=0)
    status = Column(Enum(EnumPipelineStatus, name="enum_pipeline_status"), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
