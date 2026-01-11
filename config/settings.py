# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #.env
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Telegram
    TELEGRAM_TOKEN: str

    # LLMs
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str | None = None

    # Google API
    GOOGLE_CREDENTIALS_FILE: str

    # Database
    DATABASE_URL: str


settings = Settings()
