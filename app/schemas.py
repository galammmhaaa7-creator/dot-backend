from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"

class Token(BaseModel):
    access_token: str
    token_type: str

class UserAuthResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    # Driver fields
    id_name: Optional[str] = None
    national_id: Optional[str] = None
    birth_date: Optional[datetime] = None
    id_photo_url: Optional[str] = None
    access_token: str

class LoginRequest(BaseModel):
    phone: str
    password: str

class OrderCreate(BaseModel):
    type: str # taxi or delivery
    pickup_lat: float
    pickup_lng: float
    pickup_address: Optional[str] = None
    dropoff_lat: float
    dropoff_lng: float
    dropoff_address: Optional[str] = None
    estimated_price: float
    distance_km: float

class LocationUpdate(BaseModel):
    current_lat: float
    current_lng: float

class PricingUpdate(BaseModel):
    taxi_base_price: int
    taxi_price_per_km: int
    delivery_base_price: int
    delivery_price_per_km: int
