from sqlalchemy import Column, ForeignKey, Integer, String

from backend.database import Base


class User(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    # Only password hashes belong in the database; length validation is in schemas.py.
    hashed_password = Column(String, nullable=False)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    # Store the random token ID, never the usable refresh token itself.
    jti = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    expires_at = Column(Integer, nullable=False)
