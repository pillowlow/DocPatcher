from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

from app.models.workspace import ResolvedProjectPaths
from app.services.workspace import resolve_active_project


load_dotenv()


class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gpt-5.5")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", "5"))

    project_paths: ResolvedProjectPaths = Field(default_factory=resolve_active_project)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
