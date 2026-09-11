from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.utils import get_hashed_password
from backend.model import User
from backend.schemas import UserCreate, normalize_email


class EmailAlreadyRegistered(Exception):
    pass


def get_user_by_email(db: Session, email: str):
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def create_user(db: Session, user: UserCreate):
    if get_user_by_email(db, str(user.email)):
        raise EmailAlreadyRegistered()
    db_user = User(email=normalize_email(str(user.email)), name=user.name,
                   hashed_password=get_hashed_password(user.password))
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        # The unique constraint also protects against simultaneous duplicate signups.
        db.rollback()
        if get_user_by_email(db, str(user.email)):
            raise EmailAlreadyRegistered() from None
        raise
    db.refresh(db_user)
    return db_user
