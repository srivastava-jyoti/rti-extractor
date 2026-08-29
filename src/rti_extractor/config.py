from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str
    gemini_model: str
    strapi_base_url: str
    strapi_api_token: str = ""
    work_dir: Path = Path("./data/work")
    log_level: str = "INFO"
    dry_run: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
