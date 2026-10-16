"""Application settings — validated env, no hardcoded secrets."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./insightforge.db"
    JWT_SECRET: str = "change-me-to-a-long-random-string-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000"
    MAX_UPLOAD_MB: int = 25
    UPLOAD_DIR: str = "./uploads"
    LOG_LEVEL: str = "INFO"
    BACKEND_PORT: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
