from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_email(email: str) -> str:
    # This application treats email addresses as case-insensitive login identifiers.
    return email.strip().lower()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
        return normalize_email(value) if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class UserOut(BaseModel):
    # Read ORM attributes while excluding the password hash from API responses.
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)
