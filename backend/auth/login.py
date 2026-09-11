from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.auth.utils import (ACCESS_TOKEN_LIFETIME, DUMMY_HASH, REFRESH_TOKEN_LIFETIME,
                                create_token, credentials_error, decode_token, verify_password)
from backend.crud import get_user_by_email
from backend.dependencies import get_db
from backend.model import RefreshSession, User
from backend.schemas import RefreshRequest, TokenSchema

router = APIRouter(tags=["authentication"])


def issue_tokens(db: Session, user: User, response: Response):
    access, _ = create_token(user.id, "access", ACCESS_TOKEN_LIFETIME)
    refresh, claims = create_token(user.id, "refresh", REFRESH_TOKEN_LIFETIME)
    db.execute(delete(RefreshSession).where(RefreshSession.expires_at <= int(datetime.now(timezone.utc).timestamp())))
    db.add(RefreshSession(jti=claims["jti"], user_id=user.id, expires_at=claims["exp"]))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenSchema(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenSchema)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 calls this form field 'username'; users enter their email address here.
    user = get_user_by_email(db, form_data.username)
    valid = verify_password(form_data.password, user.hashed_password if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(401, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return issue_tokens(db, user, response)


def consume_refresh_token(db: Session, token: str):
    claims = decode_token(token, "refresh")
    # An atomic delete lets a refresh token be used only once, including concurrent requests.
    result = db.execute(delete(RefreshSession).where(
        RefreshSession.jti == claims["jti"], RefreshSession.user_id == int(claims["sub"])))
    user = db.get(User, int(claims["sub"]))
    if result.rowcount != 1 or user is None:
        db.rollback()
        raise credentials_error()
    return user


@router.post("/refresh", response_model=TokenSchema)
def refresh(data: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    user = consume_refresh_token(db, data.refresh_token)
    # Removing the old session and saving its replacement happen in one transaction.
    return issue_tokens(db, user, response)


@router.post("/logout", status_code=204)
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    consume_refresh_token(db, data.refresh_token)
    db.commit()
    # Existing access tokens remain valid until their 30-minute expiry.
    return Response(status_code=204)
