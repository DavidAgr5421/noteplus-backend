"""Seed admin instructor: admin@noteplus.local / 5421

Note: password 5421 is 4 chars and violates RN-21 (min 8) — allowed only for this seed/test account.
Run: python scripts/seed_admin.py
"""
import sys
import uuid
from pathlib import Path

# Ensure app package on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.database import Base  # noqa: F401 — keeps metadata registered via models import
import app.infrastructure.persistence.models  # noqa: F401 — register tables
from app.infrastructure.persistence.models.instructor_model import InstructorModel
from app.infrastructure.security.password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_service import JwtTokenService

ADMIN_EMAIL = "admin@noteplus.local"
ADMIN_PASSWORD = "5421"
ADMIN_NOMBRE = "Admin NotePlus"


def main():
    # Use SYNC url for seeding
    sync_url = settings.SYNC_DATABASE_URL
    print(f"Connecting to {sync_url.split('@')[-1]} ...")
    engine = create_engine(sync_url, echo=False, future=True)

    # Schema is owned by Alembic migrations (entrypoint runs `alembic upgrade head`).
    # No create_all here — fail fast if migrations didn't run.

    hasher = BcryptPasswordHasher()
    jwt_service = JwtTokenService()

    with Session(engine) as session:
        existing = session.execute(
            select(InstructorModel).where(InstructorModel.email == ADMIN_EMAIL)
        ).scalar_one_or_none()

        if existing:
            print(f"Admin already exists: {existing.email} id={existing.id}")
            # Verify password and optionally update
            if not hasher.verify(ADMIN_PASSWORD, existing.password_hash):
                print("Updating password hash...")
                existing.password_hash = hasher.hash(ADMIN_PASSWORD)
                session.commit()
                print("Password updated.")
            admin = existing
        else:
            admin = InstructorModel(
                id=str(uuid.uuid4()),
                nombre=ADMIN_NOMBRE,
                email=ADMIN_EMAIL,
                password_hash=hasher.hash(ADMIN_PASSWORD),
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            print(f"Admin created: {admin.email} id={admin.id}")

        # Verify
        assert hasher.verify(ADMIN_PASSWORD, admin.password_hash), "hash verify failed"
        token = jwt_service.generate_access_token(admin.id, admin.email)
        refresh = jwt_service.generate_refresh_token(admin.id, admin.email)
        print(f"\n✓ Seed OK")
        print(f"  email: {ADMIN_EMAIL}")
        print(f"  password: {ADMIN_PASSWORD}")
        print(f"  access_token (15m): {token[:50]}...")
        print(f"  refresh_token (7d): {refresh[:50]}...")
        print(f"\nTest login:")
        print(f'  curl -s http://localhost:8000/api/v1/health | jq .')
        print(f'  # (auth endpoints Fase 1) curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d \'{{"email":"{ADMIN_EMAIL}","password":"{ADMIN_PASSWORD}"}}\'')


if __name__ == "__main__":
    main()
