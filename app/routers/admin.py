from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from app import models, schemas
from app.core import database, security

router = APIRouter(prefix="/admin", tags=["admin"])

# Dependency to check if user is admin
async def get_current_admin(current_user: models.User = Depends(security.get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    # Simple stats
    total_users = await db.scalar(select(func.count(models.User.id)).where(models.User.role == models.UserRole.CUSTOMER))
    total_drivers = await db.scalar(select(func.count(models.User.id)).where(models.User.role == models.UserRole.DRIVER))
    total_orders = await db.scalar(select(func.count(models.Order.id)))
    
    # Revenue (sum of completed orders actual_price)
    revenue_q = select(func.sum(models.Order.actual_price)).where(models.Order.status == models.OrderStatus.COMPLETED)
    total_revenue = await db.scalar(revenue_q) or 0.0
    
    return {
        "total_users": total_users,
        "total_drivers": total_drivers,
        "total_orders": total_orders,
        "total_revenue": total_revenue
    }

@router.get("/users", response_model=List[schemas.UserAuthResponse])
async def get_users(db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.User).where(models.User.role == models.UserRole.CUSTOMER))
    return result.scalars().all()

@router.get("/drivers", response_model=List[schemas.UserAuthResponse])
async def get_drivers(db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.User).where(models.User.role == models.UserRole.DRIVER))
    return result.scalars().all()

@router.get("/orders")
async def get_orders(db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.Order))
    return result.scalars().all()

@router.get("/pricing")
async def get_pricing(db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.Pricing).limit(1))
    pricing = result.scalars().first()
    if not pricing:
        # Create default if not exists
        pricing = models.Pricing()
        db.add(pricing)
        await db.commit()
        await db.refresh(pricing)
    return pricing

@router.put("/pricing")
async def update_pricing(pricing_update: schemas.PricingUpdate, db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.Pricing).limit(1))
    pricing = result.scalars().first()
    if not pricing:
        pricing = models.Pricing()
        db.add(pricing)
    
    pricing.taxi_base_price = pricing_update.taxi_base_price
    pricing.taxi_price_per_km = pricing_update.taxi_price_per_km
    pricing.delivery_base_price = pricing_update.delivery_base_price
    pricing.delivery_price_per_km = pricing_update.delivery_price_per_km
    
    await db.commit()
    return {"message": "Pricing updated"}

@router.patch("/users/{user_id}/status")
async def toggle_user_status(user_id: int, status_data: dict, db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = status_data.get('is_active', True)
    await db.commit()
    return {"message": "Status updated"}

@router.patch("/drivers/{driver_id}/status")
async def toggle_driver_status(driver_id: int, status_data: dict, db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    # Same as user, but specific endpoint for semantic clarity
    return await toggle_user_status(driver_id, status_data, db, admin)

@router.post("/wallet/top-up")
async def top_up_wallet(data: dict, db: AsyncSession = Depends(database.get_db), admin: models.User = Depends(get_current_admin)):
    driver_id = data.get('driver_id')
    amount = data.get('amount')
    
    result = await db.execute(select(models.Wallet).where(models.Wallet.driver_id == driver_id))
    wallet = result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    wallet.balance += amount
    
    # Record transaction
    trx = models.Transaction(
        wallet_id=wallet.id,
        amount=amount,
        description="Admin Top-up"
    )
    db.add(trx)
    await db.commit()
    
    return {"message": "Wallet topped up"}
