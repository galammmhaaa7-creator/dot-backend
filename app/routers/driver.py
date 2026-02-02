from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from app import models, schemas
from app.core import database, security

router = APIRouter(prefix="/driver", tags=["driver"])

# Dependency to check if user is driver
async def get_current_driver(current_user: models.User = Depends(security.get_current_user)):
    if current_user.role != models.UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not authorized, driver access only")
    return current_user

@router.get("/orders")
async def get_available_orders(db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    # Get all pending taxi and delivery orders
    # Optionally filter by location radius if geo libraries were available
    result = await db.execute(select(models.Order).where(models.Order.status == models.OrderStatus.PENDING))
    return result.scalars().all()

@router.put("/orders/{order_id}/accept")
async def accept_order(order_id: int, db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status != models.OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order already taken or cancelled")
        
    order.status = models.OrderStatus.ACCEPTED
    order.driver_id = driver.id
    
    await db.commit()
    await db.refresh(order)
    return {"message": "Order accepted", "order": order}

@router.put("/orders/{order_id}/complete")
async def complete_order(order_id: int, db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    order.status = models.OrderStatus.COMPLETED
    order.completed_at = func.now()
    
    # Calculate revenue split if needed
    # For now, just credit wallet
    # Check if driver has wallet
    wallet_res = await db.execute(select(models.Wallet).where(models.Wallet.driver_id == driver.id))
    wallet = wallet_res.scalars().first()
    
    if wallet:
        earnings = order.actual_price if order.actual_price else order.estimated_price
        wallet.balance += earnings
        
        # Add transaction
        trx = models.Transaction(
            wallet_id=wallet.id,
            amount=earnings,
            description=f"Earnings for Order #{order.id}"
        )
        db.add(trx)
    
    await db.commit()
    return {"message": "Order completed"}

@router.post("/location")
async def update_location(location: dict, db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    driver.current_lat = location.get('latitude')
    driver.current_lng = location.get('longitude')
    driver.last_location_update = func.now()
    await db.commit()
    return {"message": "Location updated"}

@router.get("/stats")
async def get_driver_stats(db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    # Completed orders
    completed_count = await db.scalar(
        select(func.count(models.Order.id))
        .where(models.Order.driver_id == driver.id)
        .where(models.Order.status == models.OrderStatus.COMPLETED)
    )
    
    return {
        "completed_orders": completed_count or 0,
        "rating": 5.0 # Placeholder
    }

@router.get("/wallet")
async def get_wallet(db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    result = await db.execute(select(models.Wallet).where(models.Wallet.driver_id == driver.id))
    wallet = result.scalars().first()
    if not wallet:
        return {"balance": 0.0}
    return wallet

@router.get("/transactions")
async def get_transactions(db: AsyncSession = Depends(database.get_db), driver: models.User = Depends(get_current_driver)):
    result = await db.execute(select(models.Wallet).where(models.Wallet.driver_id == driver.id))
    wallet = result.scalars().first()
    if not wallet:
        return []
        
    trx_res = await db.execute(select(models.Transaction).where(models.Transaction.wallet_id == wallet.id).order_by(models.Transaction.created_at.desc()))
    return trx_res.scalars().all()
