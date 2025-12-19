"""Pydantic schemas for Gemini API structured outputs"""

from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class AnalysisResponse(BaseModel):
    """コード分析結果のスキーマ"""

    is_implemented: bool = Field(
        description="タスクが既に実装されているかどうか"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="判定の信頼度（0.0-1.0）"
    )
    reasoning: str = Field(
        description="判定の理由説明"
    )
    related_files: List[str] = Field(
        default_factory=list,
        description="関連するファイルパスのリスト"
    )
    missing_components: List[str] = Field(
        default_factory=list,
        description="未実装の要素リスト"
    )


class ReferenceCode(BaseModel):
    """参考コード情報のスキーマ"""

    file_path: str = Field(
        description="参考ファイルのパス"
    )
    snippet: str = Field(
        description="重要部分のコード抜粋（10-20行程度）"
    )
    explanation: str = Field(
        description="このコードをどのように参考にすべきか"
    )


class Subtask(BaseModel):
    """サブタスク情報のスキーマ"""

    title: str = Field(
        description="Conventional Commits形式のタイトル: type(scope): description"
    )
    description: str = Field(
        description="詳細な説明"
    )
    estimated_effort: Literal["S", "M", "L"] = Field(
        description="タスクサイズ: S=小（1-2時間）, M=中（半日-1日）, L=大（2日以上）"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="依存する他のサブタスクのタイトル"
    )
    acceptance_criteria: List[str] = Field(
        description="完了条件のリスト"
    )
    reference_code: Optional[ReferenceCode] = Field(
        default=None,
        description="参考コード（ない場合はnull）"
    )


class SubtaskResponse(BaseModel):
    """タスク分解結果のスキーマ"""

    subtasks: List[Subtask] = Field(
        min_length=1,
        max_length=15,
        description="1PR粒度のサブタスクリスト"
    )


class KeywordResponse(BaseModel):
    """キーワード抽出結果のスキーマ"""

    keywords: List[str] = Field(
        min_length=1,
        max_length=10,
        description="ファイル検索用のキーワードリスト（3-5個程度推奨）"
    )
