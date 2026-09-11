"""Validated application settings, loaded from environment variables or .env."""
from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./meeting_notes.db"
    jwt_secret_key: SecretStr
    jwt_refresh_secret_key: SecretStr

    @model_validator(mode="after")
    def validate_keys(self):
        # Fail at startup instead of silently signing tokens with a default key.
        keys = [self.jwt_secret_key.get_secret_value(), self.jwt_refresh_secret_key.get_secret_value()]
        if any(len(key.encode()) < 32 for key in keys) or keys[0] == keys[1]:
            raise ValueError("JWT keys must be distinct and each at least 32 bytes")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
