import json
from pathlib import Path
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserMapping:
    """Discord IDとGitHub IDのマッピング管理"""

    def __init__(self, mapping_file: str = "user_mappings.json"):
        self.mapping_file = Path(mapping_file)
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> dict:
        """マッピングファイルを読み込み"""
        if not self.mapping_file.exists():
            logger.info(f"Mapping file {self.mapping_file} not found, creating empty mapping")
            self._save_mappings({})
            return {}

        try:
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                logger.info(f"Loaded {len(mappings)} user mappings")
                return mappings
        except Exception as e:
            logger.error(f"Failed to load mappings: {e}")
            return {}

    def _save_mappings(self, mappings: dict):
        """マッピングをファイルに保存"""
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(mappings)} user mappings")
        except Exception as e:
            logger.error(f"Failed to save mappings: {e}")

    def get_github_id(self, discord_id: str) -> Optional[str]:
        """Discord IDからGitHub IDを取得"""
        return self.mappings.get(str(discord_id))

    def set_mapping(self, discord_id: str, github_id: str):
        """マッピングを設定"""
        self.mappings[str(discord_id)] = github_id
        self._save_mappings(self.mappings)
        logger.info(f"Mapped Discord ID {discord_id} to GitHub ID {github_id}")

    def remove_mapping(self, discord_id: str):
        """マッピングを削除"""
        if str(discord_id) in self.mappings:
            del self.mappings[str(discord_id)]
            self._save_mappings(self.mappings)
            logger.info(f"Removed mapping for Discord ID {discord_id}")

    def get_all_mappings(self) -> dict:
        """全てのマッピングを取得"""
        return self.mappings.copy()
