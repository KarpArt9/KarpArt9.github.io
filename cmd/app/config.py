from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str = ""
    admin_chat_id: str = ""
    tg_proxy: str = ""

    jwt_secret: str = "change-me-in-env"
    jwt_expires_min: int = 60 * 24 * 7

    admin_username: str = "admin"
    admin_password: str = "admin123"

    db_path: Path = BASE_DIR / "data" / "app.db"
    upload_dir: Path = BASE_DIR / "data" / "uploads"


settings = Settings()
settings.db_path.parent.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
