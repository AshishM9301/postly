"""Response shapes for areas and categories."""

from pydantic import BaseModel


class AreaOut(BaseModel):
    id: str
    pincode: str
    name: str
    district: str
    lat: float
    lng: float


class AreaDetection(AreaOut):
    distance_meters: int


class AreaDetail(AreaOut):
    post_count: int


class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    sort_order: int
