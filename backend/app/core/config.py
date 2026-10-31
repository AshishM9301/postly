"""Application settings, loaded from the environment (and .env for local runs)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql://postly:postly@localhost:5432/postly"
    secret_key: str = ""
    pepper: str = ""
    rate_limit_salt: str = ""

    firebase_admin_credentials: str = ""
    firebase_project_id: str = ""
    session_ttl_days: int = 30
    ghost_post_ttl_days: int = 90
    ghost_expiry_options: str = "7,30,90,365"

    openai_api_key: str = ""
    moderation_chain: str = "rules,openai,local-hf"
    hf_model_text: str = "KoalaAI/Text-Moderation"
    hf_model_image: str = "Falconsai/nsfw_image_detection"
    hf_model_multilingual: str = "unitary/multilingual-toxic-xlm-roberta"
    hf_device: str = "cpu"

    posts_per_ip_hour: int = 5
    posts_per_ip_day: int = 20
    posts_per_area_hour: int = 50

    @property
    def is_dev(self) -> bool:
        return self.app_env.strip().lower() in {"development", "dev", "local", "test"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ghost_expiry_option_list(self) -> list[int]:
        options = {int(value) for value in self.ghost_expiry_options.split(",") if value.strip()}
        return sorted(options | {self.ghost_post_ttl_days})

    @model_validator(mode="after")
    def _require_secrets_outside_dev(self) -> "Settings":
        if not self.is_dev:
            missing = [name for name in ("secret_key", "pepper") if not getattr(self, name)]
            if missing:
                names = ", ".join(name.upper() for name in missing)
                raise ValueError(f"{names} must be set when APP_ENV={self.app_env!r}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
