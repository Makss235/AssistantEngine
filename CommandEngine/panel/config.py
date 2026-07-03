import re
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PANEL_DIR: Path = Path(__file__).resolve().parent
    STATIC_DIR: Path = PANEL_DIR / "static"
    ALLOWED_EXT: set[str] = {".json", ".py", ".md", ".yml", ".yaml", ".txt"}

    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RELOAD: bool = True


settings = Settings()