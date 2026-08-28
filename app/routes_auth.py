from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas, auth
from app.database import get_session

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    exists = await session.scalar(select(models.User).where(models.User.email == data.email))
    if exists:
        raise HTTPException(status_code=400, detail="email ja cadastrado")
    user = models.User(email=data.email, hashed_password=auth.hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
async def login(data: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(models.User).where(models.User.email == data.email))
    if not user or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="credenciais invalidas")
    token = auth.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}