from typing import List, Dict
from src.ai.gemini_client import GeminiClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskBreakdownAgent:
    """タスク分解エージェント"""

    def __init__(self):
        self.gemini = GeminiClient()

    async def break_down(
        self, task_description: str, repo_context: str
    ) -> List[Dict[str, any]]:
        """タスクをサブタスクに分解

        Args:
            task_description: タスクの説明
            repo_context: リポジトリのコンテキスト

        Returns:
            サブタスクのリスト
        """

        subtasks = await self.gemini.break_down_task(task_description, repo_context)

        logger.info(f"Broke down task into {len(subtasks)} subtasks")
        return subtasks
