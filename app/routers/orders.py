from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app import models, schemas
from app.core import database, security

router = APIRouter(prefix="/orders", tags=["orders"])

async def get_pricing(db: AsyncSession):
    result = await db.execute(select(models.Pricing).limit(1))
    pricing = result.scalars().first()
    if not pricing:
        pricing = models.Pricing()
        db.add(pricing)
        await db.commit()
    return pricing

@router.post("/taxi", response_model=schemas.BaseModel) # Using generic for now or define OrderResponse
async def create_taxi_order(
    order: schemas.OrderCreate, 
    db: AsyncSession = Depends(database.get_db), 
    current_user: models.User = Depends(security.get_current_user)
):
    pricing = await get_pricing(db)
    
    # Recalculate estimated price to be safe
    calculated_price = pricing.taxi_base_price + (order.distance_km * pricing.taxi_price_per_km)
    
    db_order = models.Order(
        customer_id=current_user.id,
        type="taxi",
        pickup_lat=order.pickup_lat,
        pickup_lng=order.pickup_lng,
        pickup_address=order.pickup_address,
        dropoff_lat=order.dropoff_lat,
        dropoff_lng=order.dropoff_lng,
        dropoff_address=order.dropoff_address,
        estimated_price=calculated_price, # Use server calculated price
        distance_km=order.distance_km,
        status=models.OrderStatus.PENDING
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    return {"id": db_order.id, "message": "Order created"}

@router.post("/delivery", response_model=schemas.BaseModel)
async def create_delivery_order(
    order: schemas.OrderCreate, 
    db: AsyncSession = Depends(database.get_db), 
    current_user: models.User = Depends(security.get_current_user)
):
    pricing = await get_pricing(db)
    
    calculated_price = pricing.delivery_base_price + (order.distance_km * pricing.delivery_price_per_km)
    
    db_order = models.Order(
        customer_id=current_user.id,
        type="delivery",
        pickup_lat=order.pickup_lat,
        pickup_lng=order.pickup_lng,
        pickup_address=order.pickup_address,
        dropoff_lat=order.dropoff_lat,
        dropoff_lng=order.dropoff_lng,
        dropoff_address=order.dropoff_address,
        estimated_price=calculated_price,
        distance_km=order.distance_km,
        status=models.OrderStatus.PENDING
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    return {"id": db_order.id, "message": "Order created"}

@router.post("/cancel")
async def cancel_order(order_data: dict, db: AsyncSession = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    order_id = order_data.get('order_id')
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if order.status in [models.OrderStatus.COMPLETED, models.OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed order")
        
    order.status = models.OrderStatus.CANCELLED
    await db.commit()
    return {"message": "Order cancelled"}

@router.get("/my-orders")
async def get_my_orders(db: AsyncSession = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    result = await db.execute(
        select(models.Order)
        .where(models.Order.customer_id == current_user.id)
        .order_by(models.Order.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{order_id}")
async def get_order_details(order_id: int, db: AsyncSession = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.driver))
        .where(models.Order.id == order_id)
    )
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.customer_id != current_user.id and order.driver_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    return order
