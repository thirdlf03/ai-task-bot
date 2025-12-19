from google import genai
from typing import List, Dict, Any
from pydantic import ValidationError
from src.config import settings
from src.utils.logger import get_logger
from src.ai.schemas import AnalysisResponse, SubtaskResponse, KeywordResponse

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
"""

        logger.info("Analyzing code implementation status with Gemini...")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": AnalysisResponse.model_json_schema(),
                }
            )

            # Pydanticでバリデーション
            result = AnalysisResponse.model_validate_json(response.text)
            result_dict = result.model_dump()

            logger.info(
                f"Analysis complete: is_implemented={result_dict['is_implemented']}, confidence={result_dict['confidence']}"
            )
            return result_dict

        except ValidationError as e:
            logger.error(f"❌ [Pydantic Validation Failed] {e}")
            logger.error(f"Response text: {response.text}")
            # フォールバック: デフォルト値を返す（分析失敗 = 実装されていないと判定）
            return {
                "is_implemented": False,
                "confidence": 0.0,
                "reasoning": f"Parse failed: {str(e)}",
                "related_files": [],
                "missing_components": [],
            }
        except Exception as e:
            logger.error(f"❌ [Analysis Failed] {e}")
            raise

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

注意: 参考コードがない場合、reference_codeはnullにしてください。
"""

        logger.info("🤖 [AI Processing] Starting task breakdown...")
        logger.info(f"📊 Repository context: {len(repo_context)} characters")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": SubtaskResponse.model_json_schema(),
                }
            )

            logger.info(f"💭 [Gemini Response Length] {len(response.text)} characters")
            logger.info(f"💭 [Gemini Response Preview]\n{response.text[:1000]}...")

            # Pydanticでバリデーション
            result = SubtaskResponse.model_validate_json(response.text)
            subtasks = [subtask.model_dump() for subtask in result.subtasks]

            logger.info(f"✅ [Task Breakdown Complete] Created {len(subtasks)} subtasks")

            # Log details of each subtask
            for i, subtask in enumerate(subtasks, 1):
                logger.info(f"📌 Subtask {i}/{len(subtasks)}: {subtask.get('title', 'No title')}")
                logger.info(f"   ├─ Size: {subtask.get('estimated_effort', 'Unknown')}")
                logger.info(f"   ├─ Dependencies: {subtask.get('dependencies', [])}")
                logger.info(f"   └─ Reference code: {'Yes' if subtask.get('reference_code') else 'No'}")

            return subtasks

        except ValidationError as e:
            logger.error(f"❌ [Pydantic Validation Failed] {e}")
            logger.error(f"Response text: {response.text}")
            # フォールバック: 空リストではなくエラーを投げる
            raise ValueError(f"Failed to parse task breakdown response: {e}") from e
        except Exception as e:
            logger.error(f"❌ [Task Breakdown Failed] {e}")
            raise

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

注意:
- キーワードは3-5個程度
- ファイル名やフォルダ名に含まれそうな単語を選ぶ
- 例: "認証機能を追加" → ["auth", "login", "user"]
"""

        logger.info("🤖 [AI Processing] Starting keyword extraction...")
        logger.info(f"📝 Task description: {task_description}")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": KeywordResponse.model_json_schema(),
                }
            )

            logger.info(f"💭 [Gemini Response]\n{response.text[:500]}...")

            # Pydanticでバリデーション
            result = KeywordResponse.model_validate_json(response.text)
            keywords = result.keywords

            logger.info(f"🔑 [Extraction Complete] Keywords: {keywords}")
            logger.info(f"💡 [AI Decision] Searching files with these keywords")

            return keywords

        except ValidationError as e:
            logger.error(f"❌ [Pydantic Validation Failed] {e}")
            logger.error(f"Response text: {response.text}")
            # フォールバック: 空リストを返す（キーワード検索をスキップ）
            logger.warning("⚠️ Keyword extraction failed, returning empty list")
            return []
        except Exception as e:
            logger.error(f"❌ [Keyword Extraction Failed] {e}")
            raise
