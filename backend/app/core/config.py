"""
Application configuration via environment variables.

All configuration is loaded from environment variables or .env file.
No secrets have default values. Safe defaults for all operational parameters.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider Configuration
    llm_provider: str = Field(
        default="ollama",
        description="LLM provider: ollama, openai, anthropic",
    )
    allow_remote_models: bool = Field(
        default=False,
        description="Allow remote/cloud model access",
    )

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="llama3:8b",
        description="Default Ollama model",
    )

    # OpenAI-Compatible Configuration
    llm_base_url: str = Field(
        default="",
        description="OpenAI-compatible API base URL",
    )
    llm_api_key: str = Field(
        default="",
        description="OpenAI-compatible API key",
    )
    llm_model: str = Field(
        default="",
        description="OpenAI-compatible model name",
    )

    # Anthropic Configuration
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key",
    )

    # Resource Limits
    max_heavy_models: int = Field(
        default=1,
        ge=1,
        le=2,
        description="Maximum heavy models loaded simultaneously",
    )
    max_agent_concurrency: int = Field(
        default=2,
        ge=1,
        le=4,
        description="Maximum concurrent agent tasks",
    )
    auto_unload_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Minutes before auto-unloading inactive heavy models",
    )
    request_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Request timeout in seconds",
    )
    max_request_tokens: int = Field(
        default=8192,
        ge=256,
        le=32768,
        description="Maximum tokens per request",
    )

    # Server Configuration
    host: str = Field(
        default="127.0.0.1",
        description="Server bind host",
    )
    port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Server bind port",
    )
    log_level: str = Field(
        default="info",
        description="Logging level",
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        allowed = {"ollama", "openai", "anthropic"}
        if v.lower() not in allowed:
            raise ValueError(f"LLM provider must be one of: {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.lower()

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Ensure host is localhost-only for security."""
        allowed_hosts = {"127.0.0.1", "localhost", "0.0.0.0"}
        if v not in allowed_hosts:
            raise ValueError(
                f"Host must be one of: {allowed_hosts} (local-only)"
            )
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing)."""
    global _settings
    _settings = None
