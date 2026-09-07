from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://vendocasa:vendocasa@localhost:5432/vendocasa"
    data_dir: str = "./data"
    google_geocoding_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""

    # Rate limiting (backend/app/services/rate_limit.py). Identity = the
    # vendocasa_uid cookie AND the client IP, checked independently.
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 50
    rate_limit_global_daily_model_calls: int = 2000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
