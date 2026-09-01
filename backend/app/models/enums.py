import enum


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


class EnumTipeRawatPuskesmas(str, enum.Enum):
    rawat_inap = "rawat_inap"
    non_rawat_inap = "non_rawat_inap"


class EnumPipelineStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class EnumUserRole(str, enum.Enum):
    public = "public"
    analyst = "analyst"
    operator = "operator"
    admin = "admin"
    superadmin = "superadmin"
