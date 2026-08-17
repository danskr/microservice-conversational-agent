from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration supplied by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")

    digest_path: str = Field(
        default="./digest/order-fulfillment-service-digest.yaml",
        alias="DIGEST_PATH",
    )
    order_service_base_url: str = Field(
        default="http://order-fulfillment-service.order-fulfillment.svc.cluster.local:8080",
        alias="ORDER_SERVICE_BASE_URL",
    )

    max_agent_steps: int = Field(default=8, ge=2, le=20, alias="MAX_AGENT_STEPS")
    request_timeout_seconds: float = Field(default=20.0, ge=1, le=120, alias="REQUEST_TIMEOUT_SECONDS")
    max_api_result_chars: int = Field(default=12000, ge=1000, le=100000, alias="MAX_API_RESULT_CHARS")
    max_digest_snippets: int = Field(default=12, ge=3, le=30, alias="MAX_DIGEST_SNIPPETS")
    confirm_conditional_actions: bool = Field(default=False, alias="CONFIRM_CONDITIONAL_ACTIONS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
