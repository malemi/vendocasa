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

    # Identity (backend/app/auth.py). SUPABASE_URL is the project URL, e.g.
    # https://<ref>.supabase.co; tokens are verified against its JWKS, or
    # against SUPABASE_JWT_SECRET when the algorithm is HS256. Without
    # SUPABASE_URL every protected route refuses with 503, never anonymously.
    supabase_url: str = ""
    supabase_jwt_algorithm: str = "ES256"
    supabase_jwt_secret: str = ""
    # The owner account (token subject) may write transaction records and
    # read spending. Empty means no account is the owner.
    owner_user_id: str = ""

    # The model is server-side configuration only -- nothing in a client
    # request can select or influence it.
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_base_url: str = DEFAULT_ANTHROPIC_BASE_URL

    # /docs and /openapi.json publish exactly which routes spend money on
    # the paid Anthropic model. Off unless explicitly enabled.
    enable_api_docs: bool = False

    # Rate limiting (backend/app/services/rate_limit.py). Identity = the
    # verified account AND the client IP, checked independently.
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 50
    rate_limit_global_daily_model_calls: int = 2000

    # Bounded cost per chat request (backend/app/services/agent.py).
    agent_max_tool_rounds: int = 3
    # Bounded by the monthly spending caps; at the limit the UI offers a new conversation.
    agent_max_history_messages: int = 50
    agent_max_message_chars: int = 4000
    agent_max_tokens: int = 4096
    # Per provider call, in seconds; well below the 15-minute window after
    # which app/services/spending.py settles a reservation left open.
    agent_call_timeout_seconds: float = 120.0
    # Total bytes of PDF/image attachments a single chat request may carry,
    # summed across every message and document_id (backend/app/api/chat.py).
    # AGENT_MAX_MESSAGE_CHARS bounds text only; without this, a request can
    # still attach AGENT_MAX_HISTORY_MESSAGES x 4 files x 5 MB and re-bill
    # that near the model's context window on every tool-calling round.
    agent_max_attachment_bytes: int = 15 * 1024 * 1024  # 15 MB

    # Monthly spending caps in US dollars (app/services/spending.py): per
    # account and in total across all accounts, per calendar month in UTC.
    account_monthly_cap_usd: float = 1.0
    global_monthly_cap_usd: float = 100.0

    # Requests per minute per account on routes that cost no provider money.
    route_requests_per_minute: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
