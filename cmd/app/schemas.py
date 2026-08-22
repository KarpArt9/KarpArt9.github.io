from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductBase(BaseModel):
    name: str
    brand: str = ""
    category: str = "split"
    price: float = 0
    area: int | None = None
    type: str = "standard"
    features: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    image: str | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    id: str | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class LeadCreate(BaseModel):
    kind: str = "callback"
    name: str = ""
    phone: str
    product_id: str | None = None
    comment: str | None = None


class LeadStatusUpdate(BaseModel):
    status: str


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    name: str
    phone: str
    product_id: str | None
    comment: str | None
    status: str
    created_at: datetime


class DashboardStats(BaseModel):
    products_total: int
    products_active: int
    leads_total: int
    leads_new: int
    leads_today: int
    leads_week: int
