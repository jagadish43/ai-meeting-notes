from fastapi import APIRouter, Depends

from backend.auth.signups import signup
from backend.dependencies import get_current_user
from backend.model import User
from backend.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])
# Preserve the original registration URL without duplicating signup logic.
router.add_api_route("/", signup, methods=["POST"], response_model=UserOut, status_code=201)


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)):
    # The dependency verifies the JWT and loads the user before this route runs.
    return user
