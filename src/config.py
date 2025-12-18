from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """アプリケーション設定"""

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

    @field_validator("GITHUB_TOKEN")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """GitHub tokenの形式検証"""
        valid_prefixes = ("ghp_", "github_pat_", "gho_", "ghs_", "ghu_")
        if not v or not v.startswith(valid_prefixes):
            raise ValueError(
                "Invalid GitHub token format. Must start with one of: ghp_, github_pat_, gho_, ghs_, ghu_"
            )
        return v

    @field_validator("DISCORD_BOT_TOKEN")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Discord bot tokenの検証"""
        if not v or len(v) < 50:
            raise ValueError("Invalid Discord bot token")
        return v

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Gemini API keyの形式検証（空の場合はスキップ）"""
        if v and not v.startswith("AIza"):
            raise ValueError("Invalid Gemini API key format. Must start with 'AIza'")
        return v


@lru_cache()
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを取得"""
    return Settings()


settings = get_settings()
