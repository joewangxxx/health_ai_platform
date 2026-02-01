"""
Admin Bootstrap Script
Run this script to ensure an admin user exists in the database.
Usage: python backend/create_first_admin.py
"""
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models import User, UserProfile
from backend.auth import get_password_hash

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # Change this immediately after first login!
DEFAULT_ADMIN_EMAIL = "admin@healthai.com"


def bootstrap_admin():
    """Ensure an admin user exists with superuser privileges."""
    print("🔧 Admin Bootstrap Script")
    print("=" * 40)
    
    # Initialize database tables if they don't exist
    init_db()
    
    with Session(engine) as session:
        # Check if admin exists
        statement = select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
        existing_admin = session.exec(statement).first()
        
        if existing_admin:
            print(f"✅ Admin user '{DEFAULT_ADMIN_USERNAME}' already exists (ID: {existing_admin.id})")
            
            # Ensure is_superuser is True
            if not existing_admin.is_superuser:
                existing_admin.is_superuser = True
                session.add(existing_admin)
                session.commit()
                print("   🔄 Updated: is_superuser set to True")
            else:
                print("   ✅ is_superuser already True")
        else:
            print(f"⚠️ Admin user not found. Creating new admin...")
            
            new_admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                is_superuser=True
            )
            session.add(new_admin)
            session.commit()
            session.refresh(new_admin)
            
            # Create profile
            profile = UserProfile(user_id=new_admin.id)
            session.add(profile)
            session.commit()
            
            print(f"   ✅ Admin created successfully!")
            print(f"   📋 Username: {DEFAULT_ADMIN_USERNAME}")
            print(f"   📋 Password: {DEFAULT_ADMIN_PASSWORD}")
            print(f"   ⚠️ SECURITY: Change the password immediately!")
    
    print("=" * 40)
    print("✅ Bootstrap complete.")


if __name__ == "__main__":
    bootstrap_admin()
