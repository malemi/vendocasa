from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://vendocasa:vendocasa@localhost:5432/vendocasa"
    data_dir: str = "./data"
    google_geocoding_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
