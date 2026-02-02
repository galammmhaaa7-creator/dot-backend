from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import aiofiles
import os
import uuid
from datetime import datetime

from app.core import security, database
from app import models, schemas
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

async def save_upload_file(file: UploadFile) -> str:
    if not file:
        return None
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    return f"/uploads/{filename}"

@router.post("/register", response_model=schemas.UserAuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    phone: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    email: Optional[str] = Form(None),
    id_name: Optional[str] = Form(None),
    national_id: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    id_photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(database.get_db)
):
    # Check if user exists
    result = await db.execute(select(models.User).where(models.User.phone == phone))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Handle file upload
    id_photo_url = None
    if id_photo:
        id_photo_url = await save_upload_file(id_photo)

    # Parse date
    parsed_birth_date = None
    if birth_date:
        try:
            parsed_birth_date = datetime.fromisoformat(birth_date)
        except ValueError:
            pass 

    hashed_password = security.get_password_hash(password)
    
    db_user = models.User(
        phone=phone,
        name=name,
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True,
        # Driver fields
        id_name=id_name,
        national_id=national_id,
        birth_date=parsed_birth_date,
        id_photo_url=id_photo_url
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Create Wallet for Driver
    if role == models.UserRole.DRIVER:
        wallet = models.Wallet(driver_id=db_user.id)
        db.add(wallet)
        await db.commit()
    
    access_token = security.create_access_token(data={"sub": db_user.phone, "role": db_user.role})
    
    return schemas.UserAuthResponse(
        id=db_user.id,
        name=db_user.name,
        phone=db_user.phone,
        email=db_user.email,
        role=db_user.role,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        id_name=db_user.id_name,
        national_id=db_user.national_id,
        birth_date=db_user.birth_date,
        id_photo_url=db_user.id_photo_url,
        access_token=access_token
    )

@router.post("/login", response_model=schemas.Token) # Simplified response for now, or match UserAuthResponse if needed
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User).where(models.User.phone == request.phone))
    user = result.scalars().first()
    
    if not user or not security.verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")
        
    access_token = security.create_access_token(data={"sub": user.phone, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile", response_model=schemas.UserAuthResponse)
async def get_profile(
    current_user: models.User = Depends(security.get_current_user)
):
    # If user is a driver, ensure we return the token as well if needed by the frontend re-auth flow
    # For now, just return the user object, PyDantic will handle the mapping except for access_token
    # Since UserAuthResponse requires access_token, we generate a fresh one or handle it differently
    # But usually /profile just returns user details. Let's adjust schemas if needed or generate a new token.
    # Refetching a token on profile view is weird but harmless.
    
    access_token = security.create_access_token(data={"sub": current_user.phone, "role": current_user.role})
    
    return schemas.UserAuthResponse(
        id=current_user.id,
        name=current_user.name,
        phone=current_user.phone,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        id_name=current_user.id_name,
        national_id=current_user.national_id,
        birth_date=current_user.birth_date,
        id_photo_url=current_user.id_photo_url,
        access_token=access_token
    )
