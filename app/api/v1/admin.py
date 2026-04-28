from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.api.deps import get_db, require_admin
from app.models.user import User, UserRole
from app.schemas.admin import CreateUserRequest, UpdateUserRequest, BatchFutureAccessRequest
from app.schemas.user import UserResponse
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(User.company_id == current_user.company_id)
        .order_by(User.full_name)
        .all()
    )


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        company_id=current_user.company_id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id,
    ).first()
    if not user:
        raise HTTPException(404, "User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.future_time_log_enabled is not None:
        user.future_time_log_enabled = payload.future_time_log_enabled
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/batch-future-access")
def batch_future_access(
    payload: BatchFutureAccessRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(
        User.id.in_(payload.user_ids),
        User.company_id == current_user.company_id,
    ).all()

    for user in users:
        user.future_time_log_enabled = payload.enabled

    db.commit()
    return {"updated": len(users), "enabled": payload.enabled}
