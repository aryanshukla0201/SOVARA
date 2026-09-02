from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

class Settings(BaseModel):
    model_provider: str = Field(
        default_factory=lambda: os.getenv("MODEL_PROVIDER", "ollama")
    )

    qwen_model: str = Field(
        default_factory=lambda: os.getenv("QWEN_MODEL", "qwen3:4b")
    )

    gemma_model: str = Field(
        default_factory=lambda: os.getenv("GEMMA_MODEL", "gemma3:latest")
    )

    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434",
        )
    )

    upload_directory: str = Field(
        default_factory=lambda: os.getenv(
            "UPLOAD_DIRECTORY",
            "data/uploads",
        )
    )

    output_directory: str = Field(
        default_factory=lambda: os.getenv(
            "OUTPUT_DIRECTORY",
            "outputs",
        )
    )

    max_repair_attempts: int = Field(
        default_factory=lambda: int(
            os.getenv("MAX_REPAIR_ATTEMPTS", "3")
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()