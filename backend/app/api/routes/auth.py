from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.database.models import User, gen_id
from app.services.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    name: str
    email: str


@router.post("/auth/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user = User(
        id=gen_id(),
        name=body.name.strip(),
        email=body.email.strip().lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == body.email.strip().lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, name=user.name, email=user.email)
