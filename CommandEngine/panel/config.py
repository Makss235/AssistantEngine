import re
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PANEL_DIR = Path(__file__).resolve().parent
    STATIC_DIR = PANEL_DIR / "static"


settings = Settings()