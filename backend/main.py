from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.auth.login import router as login_router
from backend.auth.signups import router as signup_router
from backend.database import Base, engine
from backend.routers import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables for a fresh database; existing schemas need explicit migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)
# Routers depend on shared modules, never on main, avoiding circular imports.
app.include_router(users_router)
app.include_router(signup_router)
app.include_router(login_router)


@app.get("/health")
def health_check():
    return {"status": "Running"}
