from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.auth.utils import credentials_error, decode_token
from backend.database import SessionLocal
from backend.model import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    # Each request receives its own session, which closes even when the request fails.
    with SessionLocal() as db:
        yield db


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    claims = decode_token(token, "access")
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise credentials_error()
    return user
