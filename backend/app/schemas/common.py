from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    meta: Optional[Dict[str, Any]] = None


class PaginationMeta(BaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: List[T]
    pagination: PaginationMeta


# GeoJSON Generic Contracts (RFC 7946)
class GeoJSONGeometry(BaseModel):
    type: str = Field(..., description="Point, Polygon, MultiPolygon")
    coordinates: Any


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Optional[GeoJSONGeometry] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None
