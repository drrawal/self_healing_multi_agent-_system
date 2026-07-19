"""
Application configuration – single source of truth.
All values are loaded from environment variables / .env file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "azure_openai", "groq", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # ── Self-Healing ───────────────────────────────────────────────
    max_repair_attempts: int = Field(default=3, ge=1, le=10)
    healing_timeout_seconds: int = Field(default=300, ge=30)
    learning_rate: float = Field(default=0.15, ge=0.0, le=1.0)

    # ── Memory ─────────────────────────────────────────────────────
    episodic_memory_limit: int = Field(default=1000, ge=10)
    semantic_memory_k: int = Field(default=5, ge=1)
    memory_db_path: str = "data/memory.db"

    # ── Knowledge Graph ────────────────────────────────────────────
    kg_db_path: str = "data/knowledge_graph.pkl"

    # ── Persistence ────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///data/agents.db"

    # ── API ────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_debug: bool = False

    # ── Logging ────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance (singleton)."""
    return Settings()
