from pathlib import Path

from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DB_URI: str = (
        f"sqlite:///{(ROOT_DIR / 'decidon_database' / 'prosopography.db').as_posix()}"
    )
    DB_ECHO: bool = False


settings = Settings()