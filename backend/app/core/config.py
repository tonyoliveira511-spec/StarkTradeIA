from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Nunca commitar valores reais — preencher via .env local ou secret
    # manager do ambiente de deploy (nunca no código-fonte).
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Quotex — não usada nesta fase (MVP via screenshot). Mantida na
    # config para quando a integração em tempo real for retomada (ver
    # docs/ARCHITECTURE.md, item "Ajuste de arquitetura — screenshot").
    quotex_email: str = Field(default="", alias="QUOTEX_EMAIL")
    quotex_password: str = Field(default="", alias="QUOTEX_PASSWORD")
    quotex_demo_mode: bool = Field(default=True, alias="QUOTEX_DEMO_MODE")

    database_url: str = Field(default="", alias="DATABASE_URL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_key: str = Field(default="", alias="SUPABASE_SERVICE_KEY")

    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
