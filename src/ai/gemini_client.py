import google.generativeai as genai
from typing import List, Dict, Any
import json
import re
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Gemini API クライアント"""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def analyze_code(
        self, code_context: str, task_description: str
    ) -> Dict[str, Any]:
        """コードコンテキストとタスク説明から実装状況を分析

        Args:
            code_context: リポジトリのコードコンテキスト
            task_description: タスクの説明

        Returns:
            Dict containing is_implemented, confidence, reasoning, related_files, missing_components
        """

        prompt = f"""
あなたはコード分析のエキスパートです。以下のタスクがリポジトリに実装済みか判定してください。

## タスク内容
{task_description}

## コードコンテキスト
{code_context}

以下のJSON形式で回答してください:
```json
{{
  "is_implemented": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "判定理由",
  "related_files": ["関連ファイルパス"],
  "missing_components": ["未実装の要素"]
}}
```
"""

        logger.info("Analyzing code implementation status with Gemini...")
        response = self.model.generate_content(prompt)
        result = self._parse_analysis_response(response.text)
        logger.info(
            f"Analysis complete: is_implemented={result['is_implemented']}, confidence={result['confidence']}"
        )
        return result

    async def break_down_task(
        self, task_description: str, repo_context: str
    ) -> List[Dict[str, Any]]:
        """タスクを1PR粒度のサブタスクに分解

        Args:
            task_description: タスクの説明
            repo_context: リポジトリのコンテキスト

        Returns:
            List of subtasks with title, description, estimated_effort, dependencies, acceptance_criteria
        """

        prompt = f"""
あなたはソフトウェアプロジェクトマネージャーです。以下のタスクを1PR（Pull Request）粒度のサブタスクに分解してください。

## タスク内容
{task_description}

## リポジトリコンテキスト
{repo_context}

各サブタスクは以下の条件を満たす必要があります:
- 1つのPRで完結できる粒度
- 独立して実装・テスト可能
- 明確な完了条件がある

以下のJSON形式で回答してください:
```json
{{
  "subtasks": [
    {{
      "title": "サブタスクのタイトル",
      "description": "詳細な説明",
      "estimated_effort": "S/M/L",
      "dependencies": ["依存する他のサブタスク"],
      "acceptance_criteria": ["完了条件1", "完了条件2"]
    }}
  ]
}}
```
"""

        logger.info("Breaking down task with Gemini...")
        response = self.model.generate_content(prompt)
        subtasks = self._parse_subtasks_response(response.text)
        logger.info(f"Task breakdown complete: {len(subtasks)} subtasks created")
        return subtasks

    def _parse_analysis_response(self, text: str) -> Dict[str, Any]:
        """レスポンスをパース（JSON抽出）

        Args:
            text: Gemini APIからのレスポンステキスト

        Returns:
            Dict containing analysis results
        """
        # コードブロック内のJSONを抽出
        json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 直接JSONを探す
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from: {text}")
            return {
                "is_implemented": False,
                "confidence": 0.0,
                "reasoning": "パース失敗",
                "related_files": [],
                "missing_components": [],
            }

    def _parse_subtasks_response(self, text: str) -> List[Dict[str, Any]]:
        """サブタスクレスポンスをパース

        Args:
            text: Gemini APIからのレスポンステキスト

        Returns:
            List of subtasks
        """
        json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("subtasks", [])
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(text)
            return data.get("subtasks", [])
        except json.JSONDecodeError:
            logger.error(f"Failed to parse subtasks from: {text}")
            return []
