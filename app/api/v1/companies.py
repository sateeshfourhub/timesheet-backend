from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.company import Company
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/companies", tags=["companies"])


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.employee


@router.get("/me")
def get_my_company(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    return {"id": str(company.id), "name": company.name, "slug": company.slug}


@router.get("/users")
def list_company_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/invite", status_code=201)
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_password = "ChangeMe123!"
    user = User(
        company_id=current_user.company_id,
        email=payload.email,
        hashed_password=get_password_hash(temp_password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    # TODO Phase 2: send email invite instead of returning temp password
    return {"message": "User invited", "temporary_password": temp_password}
