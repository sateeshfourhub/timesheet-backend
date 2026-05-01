import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.company import Company
from app.models.user import User, UserRole
from datetime import datetime, timezone
from app.schemas.auth import LoginRequest, TokenResponse, RegisterRequest, EmployeeRegisterRequest, CompanyRegisterRequest
from app.schemas.user import UserResponse
from app.api.deps import get_current_user
from app.models.invite_token import InviteToken

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: CompanyRegisterRequest, db: Session = Depends(get_db)):
    invite = db.query(InviteToken).filter(InviteToken.token == payload.super_admin_token).first()
    if not invite:
        raise HTTPException(status_code=403, detail="Invalid invite token")
    if invite.is_used:
        raise HTTPException(status_code=403, detail="Invite token already used")
    if invite.is_expired:
        raise HTTPException(status_code=403, detail="Invite token has expired")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = re.sub(r"[^a-z0-9-]", "-", payload.company_slug.lower()).strip("-")
    if db.query(Company).filter(Company.slug == slug).first():
        raise HTTPException(status_code=400, detail="Company slug already taken")

    company = Company(name=payload.company_name, slug=slug)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole.admin,
    )
    db.add(user)

    invite.used_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "company_id": str(company.id), "role": user.role}
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        {"sub": str(user.id), "company_id": str(user.company_id), "role": user.role}
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/employee-register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def employee_register(payload: EmployeeRegisterRequest, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == payload.company_slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found. Check your company code.")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        company_id=company.id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole.employee,
        is_active=True,
        future_time_log_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "company_id": str(user.company_id), "role": user.role}
    )
    return TokenResponse(access_token=token)
