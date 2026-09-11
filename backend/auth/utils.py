from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from backend.core import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
password_context = PasswordHash.recommended()
# Perform password verification even for unknown accounts to reduce timing differences.
DUMMY_HASH = password_context.hash("unused-dummy-password")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    try:
        return password_context.verify(password, hashed_pass)
    except (UnknownHashError, ValueError):
        return False


def credentials_error() -> HTTPException:
    return HTTPException(401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})


def token_key(kind: str) -> str:
    settings = get_settings()
    key = settings.jwt_secret_key if kind == "access" else settings.jwt_refresh_secret_key
    return key.get_secret_value()


def create_token(subject: int, kind: str, lifetime: timedelta) -> tuple[str, dict]:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(subject), "iat": int(now.timestamp()),
              "exp": int((now + lifetime).timestamp()), "type": kind, "jti": uuid4().hex}
    return jwt.encode(claims, token_key(kind), algorithm=ALGORITHM), claims


def decode_token(token: str, kind: str) -> dict:
    try:
        # Pin the algorithm and token purpose; refresh tokens cannot access protected routes.
        claims = jwt.decode(token, token_key(kind), algorithms=[ALGORITHM],
                            options={"require": ["sub", "exp", "iat", "type", "jti"]})
        if claims["type"] != kind or not claims["sub"].isascii() or not claims["sub"].isdigit():
            raise ValueError("Invalid token subject or purpose")
        if not 0 < int(claims["sub"]) <= 2**31 - 1:
            raise ValueError("Invalid user ID")
        return claims
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise credentials_error() from None
