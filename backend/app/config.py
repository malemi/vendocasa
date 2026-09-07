from pydantic_settings import BaseSettings

# The only Anthropic API host a request may ever go to. Kept as a named
# constant (not just a field default) so main.py can detect and loudly log
# an override, since the Anthropic SDK otherwise falls back to the
# ANTHROPIC_BASE_URL environment variable -- an ambient variable that has
# nothing to do with this application's own configuration.
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://vendocasa:vendocasa@localhost:5432/vendocasa"
    data_dir: str = "./data"
    google_geocoding_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""

    # The model is server-side configuration only -- nothing in a client
    # request can select or influence it.
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_base_url: str = DEFAULT_ANTHROPIC_BASE_URL

    # /docs and /openapi.json publish exactly which routes spend money on
    # the paid Anthropic model. Off unless explicitly enabled.
    enable_api_docs: bool = False

    # Rate limiting (backend/app/services/rate_limit.py). Identity = the
    # vendocasa_uid cookie AND the client IP, checked independently.
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 50
    rate_limit_global_daily_model_calls: int = 2000

    # Bounded cost per chat request (backend/app/services/agent.py).
    agent_max_tool_rounds: int = 3
    agent_max_history_messages: int = 20
    agent_max_message_chars: int = 4000
    agent_max_tokens: int = 4096

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
