from google import genai
from typing import List, Dict, Any
import json
import re
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Gemini API クライアント"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-3-flash-preview"

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
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
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
- 既存のコードがあれば、参考コードとして抜粋を含める
- **タイトルはConventional Commits形式に従う**: type(scope): description
  - type: feat, fix, docs, style, refactor, perf, test, chore のいずれか
  - scope: 変更の範囲（例: api, ui, db）- オプション
  - description: **日本語**で簡潔な説明を記述（小文字で始まる）
  - 例: "feat(reminder): リマインダーエンティティモデルを追加", "fix(db): 接続タイムアウトの問題を修正"

以下のJSON形式で回答してください:
```json
{{
  "subtasks": [
    {{
      "title": "サブタスクのタイトル",
      "description": "詳細な説明",
      "estimated_effort": "S/M/L",
      "dependencies": ["依存する他のサブタスク"],
      "acceptance_criteria": ["完了条件1", "完了条件2"],
      "reference_code": {{
        "file_path": "参考ファイルのパス",
        "snippet": "重要部分のコード抜粋（10-20行程度）",
        "explanation": "このコードをどのように参考にすべきか"
      }}
    }}
  ]
}}
```

注意: 参考コードがない場合、reference_codeはnullにしてください。
"""

        logger.info("🤖 [AI Processing] Starting task breakdown...")
        logger.info(f"📊 Repository context: {len(repo_context)} characters")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        logger.info(f"💭 [Gemini Response Length] {len(response.text)} characters")
        logger.info(f"💭 [Gemini Response Preview]\n{response.text[:1000]}...")

        subtasks = self._parse_subtasks_response(response.text)

        logger.info(f"✅ [Task Breakdown Complete] Created {len(subtasks)} subtasks")

        # Log details of each subtask
        for i, subtask in enumerate(subtasks, 1):
            logger.info(f"📌 Subtask {i}/{len(subtasks)}: {subtask.get('title', 'No title')}")
            logger.info(f"   ├─ Size: {subtask.get('estimated_effort', 'Unknown')}")
            logger.info(f"   ├─ Dependencies: {subtask.get('dependencies', [])}")
            logger.info(f"   └─ Reference code: {'Yes' if subtask.get('reference_code') else 'No'}")

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
                "reasoning": "Parse failed",
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

    async def extract_keywords(self, task_description: str) -> List[str]:
        """タスク説明からファイル検索用のキーワードを抽出

        Args:
            task_description: タスクの説明

        Returns:
            検索キーワードのリスト
        """
        prompt = f"""
あなたはコード分析のエキスパートです。以下のタスク内容から、関連するコードファイルを検索するためのキーワードを抽出してください。

## タスク内容
{task_description}

以下のJSON形式で回答してください:
```json
{{
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}
```

注意:
- キーワードは3-5個程度
- ファイル名やフォルダ名に含まれそうな単語を選ぶ
- 例: "認証機能を追加" → ["auth", "login", "user"]
"""

        logger.info("🤖 [AI Processing] Starting keyword extraction...")
        logger.info(f"📝 Task description: {task_description}")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        logger.info(f"💭 [Gemini Response]\n{response.text[:500]}...")

        result = self._parse_keywords_response(response.text)
        keywords = result.get("keywords", [])

        logger.info(f"🔑 [Extraction Complete] Keywords: {keywords}")
        logger.info(f"💡 [AI Decision] Searching files with these keywords")

        return keywords

    def _parse_keywords_response(self, text: str) -> Dict[str, List[str]]:
        """キーワード抽出レスポンスをパース

        Args:
            text: Gemini APIからのレスポンステキスト

        Returns:
            Dict containing keywords list
        """
        json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse keywords from: {text}")
            return {"keywords": []}
