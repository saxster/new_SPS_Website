import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv()


class DatabaseConfig(BaseModel):
    path: str = ".agent/content_brain.db"
    backup_path: str = ".agent/content_brain_backup.db"


class LLMConfig(BaseModel):
    model: str = "gemini-3-pro-preview"
    temperature: float = 0.7
    max_retries: int = 3
    timeout: int = 60


class ContentSpec(BaseModel):
    min_words: int
    min_sections: int
    min_sources: int
    min_regulations: int


class PathsConfig(BaseModel):
    drafts_dir: str = "drafts"
    output_dir: str = "output"
    rules_dir: str = ".agent/rules"
    website_content_dir: str = "website/src/content/blog"


class Settings(BaseSettings):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    content_specs: Dict[str, ContentSpec] = Field(default_factory=dict)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    news_miner: Dict[str, Any] = Field(default_factory=dict)
    research: Dict[str, Any] = Field(default_factory=dict)
    fact_check: Dict[str, Any] = Field(default_factory=dict)
    citation: Dict[str, Any] = Field(default_factory=dict)
    topic_dedup: Dict[str, Any] = Field(default_factory=dict)
    newsroom: Dict[str, Any] = Field(default_factory=dict)
    claims: Dict[str, Any] = Field(default_factory=dict)
    publish_policy: Dict[str, Any] = Field(default_factory=dict)
    updates: Dict[str, Any] = Field(default_factory=dict)

    # Multi-source miner configuration
    miners: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "youtube": {"enabled": False},
            "article": {"enabled": False},
            "paper": {"enabled": True},
        }
    )

    # Trust layer configuration
    trust: Dict[str, Any] = Field(
        default_factory=lambda: {
            "block_on_low_confidence": True,
            "min_confidence_score": 5.0,
            "require_multi_source_for_numeric": True,
            "min_sources_per_claim": 2,
            "warn_on_single_source": True,
        }
    )

    # Pipeline profiles for content-type specific publishing
    pipeline_profiles: Dict[str, Any] = Field(default_factory=dict)

    # Trusted sources by tier for breaking news fast-track
    trusted_sources: Dict[str, Any] = Field(default_factory=dict)

    # Secrets (Loaded from env)
    GOOGLE_API_KEY: Optional[str] = Field(None, validation_alias="GOOGLE_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", extra="ignore"
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> "Settings":
        if not yaml_path.exists():
            raise FileNotFoundError(f"Config file not found at {yaml_path}")

        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        return cls(**yaml_data)


class ConfigManager:
    _instance = None
    _settings: Settings

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = Path(__file__).parent / "settings.yaml"
        try:
            self._settings = Settings.load_from_yaml(config_path)
            self._validate_secrets()
        except Exception as e:
            # Re-raise as a configuration error rather than hard exit
            raise RuntimeError(f"Failed to load configuration: {e}")

    def _validate_secrets(self):
        if not self._settings.GOOGLE_API_KEY:
            # We log a warning or raise depending on strictness.
            # For now, let's warn but not crash until the key is actually needed.
            import logging

            logging.getLogger("Config").warning(
                "GOOGLE_API_KEY is not set in environment."
            )

    @property
    def settings(self) -> Settings:
        return self._settings

    def get(self, key: str, default=None) -> Any:
        """
        Dot notation access to config (e.g., 'llm.model').
        Backward compatibility wrapper.
        """
        keys = key.split(".")
        value = self._settings
        try:
            for k in keys:
                if isinstance(value, BaseModel):
                    value = getattr(value, k)
                elif isinstance(value, dict):
                    value = value[k]
                else:
                    return default
            return value
        except (AttributeError, KeyError):
            return default


# Global Accessor
config = ConfigManager()
