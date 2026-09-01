from backend.app.schemas.common import (
    APIResponse,
    PaginationMeta,
    PaginatedResponse,
    GeoJSONGeometry,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
)
from backend.app.schemas.wilayah import (
    WilayahBase,
    WilayahAgregatSummary,
    WilayahDetail,
    ChoroplethWilayahItem,
)
from backend.app.schemas.faskes import (
    FaskesBase,
    RumahSakitDetail,
    PuskesmasDetail,
    FaskesNearbyFilter,
    FaskesNearbyItem,
)
from backend.app.schemas.indikator import (
    IndikatorItem,
    IndikatorTrendPoint,
    IndikatorTrendResponse,
    SDMSummaryItem,
)
from backend.app.schemas.katalog import DatasetKatalogItem
from backend.app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    UserProfile,
)
from backend.app.schemas.ask import (
    AskDataRequest,
    AskDataCitation,
    AskDataResponse,
)

__all__ = [
    "APIResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "GeoJSONGeometry",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    "WilayahBase",
    "WilayahAgregatSummary",
    "WilayahDetail",
    "ChoroplethWilayahItem",
    "FaskesBase",
    "RumahSakitDetail",
    "PuskesmasDetail",
    "FaskesNearbyFilter",
    "FaskesNearbyItem",
    "IndikatorItem",
    "IndikatorTrendPoint",
    "IndikatorTrendResponse",
    "SDMSummaryItem",
    "DatasetKatalogItem",
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "TokenRefreshRequest",
    "UserProfile",
    "AskDataRequest",
    "AskDataCitation",
    "AskDataResponse",
]
