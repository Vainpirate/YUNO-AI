from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YUNO Agent Orchestration API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # SQLite is the default so the app starts out-of-the-box without PostgreSQL.
    # Switch to postgresql+psycopg://... in .env (or docker-compose) for production.
    database_url: str = "sqlite:///./yuno_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    gemini_api_key: str = ""
    telegram_bot_token: str = ""

    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
