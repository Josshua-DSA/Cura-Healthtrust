from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from backend.app.core.database import Base
from backend.app.models.enums import EnumTipeWilayah


class RefWilayah(Base):
    __tablename__ = "ref_wilayah"

    kode_bps = Column(String(4), primary_key=True)  # contoh: '3578'
    nama_wilayah = Column(String(100), nullable=False)
    tipe = Column(Enum(EnumTipeWilayah, name="enum_tipe_wilayah"), nullable=False)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rumah_sakit = relationship("TblRumahSakit", back_populates="wilayah", lazy="selectin")
    puskesmas = relationship("FaskesPuskesmas", back_populates="wilayah", lazy="selectin")
    penduduk = relationship("TblPenduduk", back_populates="wilayah", lazy="selectin")
    agregat = relationship("TblAgregatWilayah", back_populates="wilayah", lazy="selectin")
    indikator = relationship("TblIndikatorKesehatan", back_populates="wilayah", lazy="selectin")
