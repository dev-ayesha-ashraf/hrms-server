from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:3000"

    # Public base URL used to build asset URLs (e.g. avatar links)
    BASE_URL: str = "http://127.0.0.1:8000"

    # Rate limiting — slowapi format, e.g. "60/minute"
    RATE_LIMIT: str = "60/minute"

    # Dashboard stats cache TTL in seconds
    DASHBOARD_CACHE_TTL: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
