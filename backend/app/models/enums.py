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


class EnumJenisNakes(str, enum.Enum):
    dokter_umum = "dokter_umum"
    dokter_spesialis = "dokter_spesialis"
    dokter_gigi = "dokter_gigi"
    perawat = "perawat"
    bidan = "bidan"
    ahli_gizi = "ahli_gizi"
    anestesi = "anestesi"
    sanitarian = "sanitarian"
    apoteker = "apoteker"
    tenaga_lab = "tenaga_lab"


class EnumFaskesLevel(str, enum.Enum):
    RS = "RS"
    Puskesmas = "Puskesmas"
    Dinas = "Dinas"
    Klinik = "Klinik"
    Semua_Faskes = "Semua Faskes"


class EnumTipePelayananPenyakit(str, enum.Enum):
    rawat_inap = "rawat_inap"
    rawat_jalan = "rawat_jalan"
    igd = "igd"


class EnumStatusKasusPenyakit(str, enum.Enum):
    menular = "menular"
    tidak_menular = "tidak_menular"
