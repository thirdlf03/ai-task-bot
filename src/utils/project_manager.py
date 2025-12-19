import json
from pathlib import Path
from typing import Optional
from src.utils.logger import get_logger
from src.config import settings

logger = get_logger(__name__)


class ProjectManager:
    """Discord IDとGitHub Project番号のマッピング管理"""

    def __init__(self, mapping_file: str = "user_projects.json"):
        self.mapping_file = Path(mapping_file)
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> dict:
        """マッピングファイルを読み込み"""
        if not self.mapping_file.exists():
            logger.info(f"Project mapping file {self.mapping_file} not found, creating empty mapping")
            self._save_mappings({})
            return {}

        try:
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                logger.info(f"Loaded {len(mappings)} user project mappings")
                return mappings
        except Exception as e:
            logger.error(f"Failed to load project mappings: {e}")
            return {}

    def _save_mappings(self, mappings: dict):
        """マッピングをファイルに保存"""
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(mappings)} user project mappings")
        except Exception as e:
            logger.error(f"Failed to save project mappings: {e}")

    def get_project_number(self, discord_id: str) -> int:
        """Discord IDからプロジェクト番号を取得（未設定の場合はデフォルト値）"""
        project_num = self.mappings.get(str(discord_id))
        if project_num is None:
            logger.debug(f"No project set for Discord ID {discord_id}, using default: {settings.GITHUB_PROJECT_NUMBER}")
            return settings.GITHUB_PROJECT_NUMBER
        return int(project_num)

    def set_project(self, discord_id: str, project_number: int):
        """ユーザーのプロジェクト番号を設定"""
        self.mappings[str(discord_id)] = project_number
        self._save_mappings(self.mappings)
        logger.info(f"Set project {project_number} for Discord ID {discord_id}")

    def remove_project(self, discord_id: str):
        """ユーザーのプロジェクト設定を削除（デフォルトに戻る）"""
        if str(discord_id) in self.mappings:
            del self.mappings[str(discord_id)]
            self._save_mappings(self.mappings)
            logger.info(f"Removed project setting for Discord ID {discord_id}")

    def get_all_mappings(self) -> dict:
        """全てのマッピングを取得"""
        return self.mappings.copy()
