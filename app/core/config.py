"""Settings loaded from environment variables or a local .env file. No secrets live in source."""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_PREFIX = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_base_url: str = "http://localhost:8000"
    gateway_mode: Literal["mock", "egras"] = "mock"

    # Shared key your department backend sends in the X-API-Key header.
    api_key: str = ""
    # Mock gateway only: signs the simulated eGRAS callbacks.
    mock_callback_secret: str = ""

    # eGRAS values issued to your department by the state treasury / eGRAS team.
    # Never commit them. Names here are generic; map them to your integration document.
    egras_payment_url: str = ""
    egras_verification_url: str = ""
    egras_merchant_code: str = ""
    egras_secret_key: str = ""

    def validate_runtime(self) -> None:
        if len(self.api_key) < 32:
            raise ValueError("API_KEY must be set and at least 32 characters long.")
        if self.gateway_mode == "mock":
            if self.app_env == "production":
                raise ValueError("The mock gateway must not run in production.")
            if len(self.mock_callback_secret) < 32:
                raise ValueError("MOCK_CALLBACK_SECRET must be set and at least 32 characters long.")
            if self.mock_callback_secret == self.api_key:
                raise ValueError("API_KEY and MOCK_CALLBACK_SECRET must be different.")
        else:
            required = ("egras_payment_url", "egras_verification_url", "egras_merchant_code", "egras_secret_key")
            missing = [name.upper() for name in required if not getattr(self, name)]
            if missing:
                raise ValueError("GATEWAY_MODE=egras requires: " + ", ".join(missing))
            if not (self.egras_payment_url.startswith("https://") and self.egras_verification_url.startswith("https://")):
                raise ValueError("eGRAS URLs must use HTTPS.")
        if self.app_env == "production" and self.api_key.startswith(PLACEHOLDER_PREFIX):
            raise ValueError("Replace the example API_KEY before production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
