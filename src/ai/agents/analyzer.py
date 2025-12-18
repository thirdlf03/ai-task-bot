from pathlib import Path
from typing import Dict, Any
from src.ai.gemini_client import GeminiClient
from src.repository.analyzer import RepositoryAnalyzer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryAnalysisAgent:
    """リポジトリ分析エージェント"""

    def __init__(self):
        self.gemini = GeminiClient()

    async def analyze_implementation_status(
        self, repo_path: Path, task_description: str
    ) -> Dict[str, Any]:
        """タスクの実装状況を分析

        Args:
            repo_path: リポジトリパス
            task_description: タスクの説明

        Returns:
            分析結果（is_implemented, confidence, reasoning, related_files, missing_components）
        """

        analyzer = RepositoryAnalyzer(repo_path)

        # プロジェクト構造を取得
        file_tree = analyzer.get_file_tree()
        project_summary = analyzer.get_project_summary()

        # タスクに関連しそうなファイルを検索
        search_patterns = self._extract_search_patterns(task_description)
        relevant_files = []
        for pattern in search_patterns:
            relevant_files.extend(analyzer.search_files(pattern))

        # 関連ファイルの内容を取得
        code_content = analyzer.read_code_files(relevant_files[:10])  # 最大10ファイル

        # コンテキストを構築
        context = f"""
# プロジェクト構造
{file_tree}

# プロジェクトサマリー
- ファイル数: {project_summary["file_counts"]}
- 総行数: {project_summary["total_lines"]}
- 主要言語: {project_summary["primary_language"]}

# 関連コード
{code_content}
"""

        # Geminiで分析
        analysis = await self.gemini.analyze_code(context, task_description)

        logger.info(
            f"Analysis result: {analysis['is_implemented']} (confidence: {analysis['confidence']})"
        )
        return analysis

    def _extract_search_patterns(self, task_description: str) -> list[str]:
        """タスク説明から検索パターンを抽出（簡易版）

        Args:
            task_description: タスクの説明

        Returns:
            検索パターンのリスト
        """
        # 実際にはNLPやキーワード抽出を使用するとより良い
        keywords = [
            "auth",
            "login",
            "user",
            "api",
            "database",
            "config",
            "task",
            "bot",
            "command",
        ]
        patterns = []

        desc_lower = task_description.lower()
        for keyword in keywords:
            if keyword in desc_lower:
                patterns.append(f"**/*{keyword}*.py")
                patterns.append(f"**/*{keyword}*.ts")
                patterns.append(f"**/*{keyword}*.js")

        if not patterns:
            patterns = ["**/*.py", "**/*.ts", "**/*.js"]

        return patterns[:5]  # 最大5パターン
