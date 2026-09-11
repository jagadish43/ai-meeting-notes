from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.crud import EmailAlreadyRegistered, create_user
from backend.dependencies import get_db
from backend.schemas import UserCreate, UserOut

router = APIRouter(tags=["authentication"])


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(data: UserCreate, db: Session = Depends(get_db)):
    # Both signup endpoints use this same database and password-hashing path.
    try:
        return create_user(db, data)
    except EmailAlreadyRegistered:
        raise HTTPException(409, "Email already registered") from None
