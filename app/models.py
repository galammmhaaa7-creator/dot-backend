from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Driver Specific Fields
    id_name = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    id_photo_url = Column(String, nullable=True)
    
    # Driver Location
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    orders_as_customer = relationship("Order", foreign_keys="[Order.customer_id]", back_populates="customer")
    orders_as_driver = relationship("Order", foreign_keys="[Order.driver_id]", back_populates="driver")
    wallet = relationship("Wallet", back_populates="driver", uselist=False)

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=0.0)

    driver = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wallet = relationship("Wallet", back_populates="transactions")

class Pricing(Base):
    __tablename__ = "pricing"

    id = Column(Integer, primary_key=True, index=True)
    taxi_base_price = Column(Float, default=10.0)
    taxi_price_per_km = Column(Float, default=2.0)
    delivery_base_price = Column(Float, default=15.0)
    delivery_price_per_km = Column(Float, default=2.5)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    type = Column(String, nullable=False) # 'taxi' or 'delivery'
    status = Column(String, default=OrderStatus.PENDING)
    
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    pickup_address = Column(String, nullable=True)
    
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    dropoff_address = Column(String, nullable=True)
    
    estimated_price = Column(Float, nullable=False)
    actual_price = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders_as_customer")
    driver = relationship("User", foreign_keys=[driver_id], back_populates="orders_as_driver")
    rating = relationship("Rating", back_populates="order", uselist=False)

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="rating")
