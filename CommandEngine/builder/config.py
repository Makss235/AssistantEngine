from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    BUILDER: Path = Path(__file__).resolve().parent
    CORE: Path = BUILDER.parent
    MODULES: Path = CORE / "modules"
    SHARED: Path = MODULES / "_shared"
    RASA: Path = CORE / "rasa"
    DATA: Path = RASA / "data"
    SCHEMA_FILE: Path = BUILDER / "schemas" / "manifest.schema.json"


settings = Settings()