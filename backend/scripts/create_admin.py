"""Script to create an initial admin user safely.

Usage:
    ADMIN_EMAIL=admin@example.cl ADMIN_PASSWORD=securepass ADMIN_DISPLAY_NAME="Javier" \
    uv run python scripts/create_admin.py [--force]
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid

from sqlalchemy import func

from app.core.auth import hash_password
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.admin_user import AdminUser
from app.models.business import Business


def main():
    force_update = "--force" in sys.argv

    email = settings.ADMIN_EMAIL.strip()
    password = settings.ADMIN_PASSWORD
    display_name = settings.ADMIN_DISPLAY_NAME.strip()
    business_id_str = settings.BUSINESS_ID.strip()

    if not email:
        print("Error: ADMIN_EMAIL no está configurado.", file=sys.stderr)
        sys.exit(1)

    if not password or len(password) < 8:
        print("Error: ADMIN_PASSWORD debe tener al menos 8 caracteres.", file=sys.stderr)
        sys.exit(1)

    if not display_name:
        print("Error: ADMIN_DISPLAY_NAME no está configurado.", file=sys.stderr)
        sys.exit(1)

    try:
        business_id = uuid.UUID(business_id_str)
    except ValueError:
        print(f"Error: BUSINESS_ID '{business_id_str}' no es un UUID válido.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            print(f"Error: El negocio con ID '{business_id}' no existe en la base de datos.", file=sys.stderr)
            sys.exit(1)

        normalized_email = email.lower()
        existing_admin = (
            db.query(AdminUser)
            .filter(
                AdminUser.business_id == business_id,
                func.lower(AdminUser.email) == normalized_email,
            )
            .first()
        )

        pwd_hash = hash_password(password)

        if existing_admin:
            if force_update:
                existing_admin.password_hash = pwd_hash
                existing_admin.display_name = display_name
                existing_admin.is_active = True
                db.commit()
                print(f"Administrador '{normalized_email}' actualizado exitosamente para el negocio '{business.name}'.")
            else:
                print(
                    f"El administrador '{normalized_email}' ya existe para el negocio '{business.name}'. "
                    "Usa --force para actualizar credenciales."
                )
        else:
            admin_user = AdminUser(
                business_id=business_id,
                email=normalized_email,
                password_hash=pwd_hash,
                display_name=display_name,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"Administrador '{normalized_email}' creado exitosamente para el negocio '{business.name}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
