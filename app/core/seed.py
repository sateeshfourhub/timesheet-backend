from app.core.database import SessionLocal
from app.models.company import Company
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def seed_superadmin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "sateesh@fourhubtech.com").first()
        if existing:
            if not existing.is_superuser:
                existing.is_superuser = True
                db.commit()
                print("Updated sateesh@fourhubtech.com to superuser")
            return

        company = db.query(Company).filter(Company.slug == "fourhub").first()
        if not company:
            company = Company(name="Fourhub Tech", slug="fourhub")
            db.add(company)
            db.flush()

        user = User(
            company_id=company.id,
            email="sateesh@fourhubtech.com",
            hashed_password=get_password_hash("Opendoor44##"),
            full_name="Sateesh Biyyala",
            role=UserRole.admin,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        print("Superadmin created: sateesh@fourhubtech.com")
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
    finally:
        db.close()
