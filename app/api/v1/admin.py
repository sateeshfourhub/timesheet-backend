import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional
from app.api.deps import get_db, require_admin
from app.models.user import User, UserRole
from app.models.company import Company
from app.models.invite_token import InviteToken
from app.schemas.admin import CreateUserRequest, UpdateUserRequest, BatchFutureAccessRequest
from app.schemas.user import UserResponse
from app.core.security import get_password_hash
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/companies")
def list_companies(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(403, "Superadmin only")
    companies = (
        db.query(Company)
        .filter(Company.is_active == True)
        .order_by(Company.name)
        .all()
    )
    return [{"id": str(c.id), "name": c.name} for c in companies]


@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User).options(joinedload(User.company))
    if not current_user.is_superuser:
        q = q.filter(User.company_id == current_user.company_id)
    return q.order_by(User.full_name).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    company_id = current_user.company_id
    if current_user.is_superuser and payload.company_id:
        if not db.query(Company).filter(Company.id == payload.company_id).first():
            raise HTTPException(400, "Company not found")
        company_id = payload.company_id

    user = User(
        company_id=company_id,
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
    q = db.query(User).filter(User.id == user_id)
    if not current_user.is_superuser:
        q = q.filter(User.company_id == current_user.company_id)
    user = q.first()
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


class InviteTokenRequest(BaseModel):
    company_name: Optional[str] = None


@router.post("/invite-tokens", status_code=201)
def create_invite_token(
    payload: InviteTokenRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(403, "Superadmin only")

    token = InviteToken(
        token=secrets.token_hex(32),
        company_name=payload.company_name,
        created_by=current_user.id,
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    return {
        "token": token.token,
        "company_name": token.company_name,
        "expires_at": token.expires_at.isoformat(),
        "created_at": token.created_at.isoformat(),
    }


@router.get("/invite-tokens")
def list_invite_tokens(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(403, "Superadmin only")

    tokens = db.query(InviteToken).order_by(InviteToken.created_at.desc()).all()
    now = datetime.now(timezone.utc)

    return [
        {
            "token": t.token,
            "company_name": t.company_name,
            "expires_at": t.expires_at.isoformat(),
            "created_at": t.created_at.isoformat(),
            "used_at": t.used_at.isoformat() if t.used_at else None,
            "status": "used" if t.used_at else ("expired" if now > t.expires_at else "active"),
        }
        for t in tokens
    ]


@router.post("/users/batch-future-access")
def batch_future_access(
    payload: BatchFutureAccessRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User).filter(User.id.in_(payload.user_ids))
    if not current_user.is_superuser:
        q = q.filter(User.company_id == current_user.company_id)
    users = q.all()

    for user in users:
        user.future_time_log_enabled = payload.enabled

    db.commit()
    return {"updated": len(users), "enabled": payload.enabled}
