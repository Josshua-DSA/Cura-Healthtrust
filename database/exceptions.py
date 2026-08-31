"""
Custom Exception Hierarchy — Cura HealthTrust Facilities
Sesuai RULES.md Seksi 5: Fail loudly di development, fail gracefully di production.
"""


class CuraBaseError(Exception):
    """Base untuk semua exception Cura."""
    pass


class FetchError(CuraBaseError):
    """Gagal mengambil data dari sumber eksternal."""
    pass


class ValidationError(CuraBaseError):
    """Data tidak lolos validasi schema."""
    pass


class GeocodeError(CuraBaseError):
    """Gagal melakukan geocoding koordinat."""
    pass


class LoadError(CuraBaseError):
    """Gagal memuat data ke database."""
    pass


class PipelineError(CuraBaseError):
    """Error umum pada eksekusi pipeline ETL."""
    pass
