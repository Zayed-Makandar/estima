from sqlmodel import Session, select

from ..models.user import User, UserRole
from ..auth.security import hash_password


def seed_initial_users(session: Session) -> None:
    """Seed the admin and normal user if they don't exist."""
    
    # Check if admin exists
    admin_stmt = select(User).where(User.email == "admin@ats")
    existing_admin = session.exec(admin_stmt).first()
    
    if not existing_admin:
        admin = User(
            username="admin",
            email="admin@ats",
            hashed_password=hash_password("admin@1124"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        print("Created admin user: admin@ats")
    
    # Check if zayed user exists
    zayed_stmt = select(User).where(User.username == "zayed")
    existing_zayed = session.exec(zayed_stmt).first()
    
    if not existing_zayed:
        zayed = User(
            username="zayed",
            email="zayed@estim.local",
            hashed_password=hash_password("zayed@2003"),
            role=UserRole.NORMAL,
            is_active=True,
        )
        session.add(zayed)
        print("Created normal user: zayed")
    
    session.commit()
