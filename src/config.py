from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord
    DISCORD_BOT_TOKEN: str
    DISCORD_GUILD_ID: int

    # GitHub
    GITHUB_TOKEN: str
    GITHUB_ORG: str
    GITHUB_REPO: str
    GITHUB_PROJECT_NUMBER: int

    # Gemini
    GEMINI_API_KEY: str = ""  # Phase 2で使用

    # Repository
    CLONE_DIR: str = "/tmp/ai-task-bot-repos"
    CLONE_DEPTH: int = 1

    # Rate Limiting
    GITHUB_API_MAX_REQUESTS: int = 5000
    GITHUB_API_WINDOW_SECONDS: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"

    # Title Validation
    VALIDATE_CONVENTIONAL_COMMITS: bool = True
    AUTO_FIX_TITLES: bool = True

    # Duplicate Detection
    CHECK_DUPLICATES: bool = True
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.8
    INCLUDE_CLOSED_IN_DUPLICATE_CHECK: bool = False

    # GitHub Projects Status
    DEFAULT_PROJECT_STATUS: str = "Backlog"

    @field_validator("GITHUB_TOKEN")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """Validate GitHub token format"""
        valid_prefixes = ("ghp_", "github_pat_", "gho_", "ghs_", "ghu_")
        if not v or not v.startswith(valid_prefixes):
            raise ValueError(
                "Invalid GitHub token format. Must start with one of: ghp_, github_pat_, gho_, ghs_, ghu_"
            )
        return v

    @field_validator("DISCORD_BOT_TOKEN")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord bot token"""
        if not v or len(v) < 50:
            raise ValueError("Invalid Discord bot token")
        return v

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key format (skip if empty)"""
        if v and not v.startswith("AIza"):
            raise ValueError("Invalid Gemini API key format. Must start with 'AIza'")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get singleton instance of settings"""
    return Settings()


settings = get_settings()
