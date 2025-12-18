import asyncio
from typing import TypedDict
from pathlib import Path
from langgraph.graph import StateGraph, END
from src.ai.agents.analyzer import RepositoryAnalysisAgent
from src.ai.agents.task_breaker import TaskBreakdownAgent
from src.repository.cloner import RepositoryCloner
from src.repository.analyzer import RepositoryAnalyzer
from src.github.client import GitHubClient
from src.github.mutations import CREATE_ISSUE, ADD_TO_PROJECT
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowState(TypedDict):
    """ワークフロー状態"""

    task_description: str
    repo_url: str
    repo_path: Path | None
    is_implemented: bool
    confidence: float
    subtasks: list
    created_issues: list
    error: str


class CreateTaskWorkflow:
    """タスク作成ワークフロー"""

    def __init__(self):
        self.cloner = RepositoryCloner()
        self.analyzer_agent = RepositoryAnalysisAgent()
        self.breakdown_agent = TaskBreakdownAgent()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """LangGraphワークフローを構築"""

        workflow = StateGraph(WorkflowState)

        # ノード追加
        workflow.add_node("clone_repo", self._clone_repo)
        workflow.add_node("analyze_implementation", self._analyze_implementation)
        workflow.add_node("breakdown_task", self._breakdown_task)
        workflow.add_node("create_issues", self._create_issues)

        # エッジ追加
        workflow.set_entry_point("clone_repo")
        workflow.add_edge("clone_repo", "analyze_implementation")
        workflow.add_conditional_edges(
            "analyze_implementation",
            self._should_create_tasks,
            {"create": "breakdown_task", "skip": END},
        )
        workflow.add_edge("breakdown_task", "create_issues")
        workflow.add_edge("create_issues", END)

        return workflow.compile()

    async def _clone_repo(self, state: WorkflowState) -> WorkflowState:
        """リポジトリをクローン"""
        try:
            logger.info(f"Cloning repository: {state['repo_url']}")
            repo_path = await self.cloner.clone_or_update(state["repo_url"])
            state["repo_path"] = repo_path
            logger.info(f"Repository cloned to: {repo_path}")
        except Exception as e:
            state["error"] = f"Clone failed: {str(e)}"
            logger.error(state["error"], exc_info=True)

        return state

    async def _analyze_implementation(self, state: WorkflowState) -> WorkflowState:
        """実装状況を分析"""
        try:
            logger.info("Analyzing implementation status")
            analysis = await self.analyzer_agent.analyze_implementation_status(
                state["repo_path"], state["task_description"]
            )

            state["is_implemented"] = analysis["is_implemented"]
            state["confidence"] = analysis["confidence"]

            logger.info(
                f"Analysis complete: implemented={state['is_implemented']}, "
                f"confidence={state['confidence']}"
            )
        except Exception as e:
            state["error"] = f"Analysis failed: {str(e)}"
            logger.error(state["error"], exc_info=True)

        return state

    def _should_create_tasks(self, state: WorkflowState) -> str:
        """タスク作成が必要か判定"""
        if state.get("error"):
            return "skip"

        # 実装済みまたは高信頼度で実装済みと判定
        if state["is_implemented"] and state["confidence"] > 0.7:
            logger.info("Task already implemented, skipping creation")
            return "skip"

        return "create"

    async def _breakdown_task(self, state: WorkflowState) -> WorkflowState:
        """タスクを分解"""
        try:
            logger.info("=" * 80)
            logger.info("🚀 [ワークフロー] タスク分解フェーズ開始")
            logger.info("=" * 80)
            logger.info(f"📝 タスク: {state['task_description']}")

            # リポジトリコンテキストを取得
            analyzer = RepositoryAnalyzer(state["repo_path"])
            file_tree = analyzer.get_file_tree()
            summary = analyzer.get_project_summary()

            logger.info("\n" + "─" * 80)
            logger.info("📍 [フェーズ 1/3] キーワード抽出")
            logger.info("─" * 80)

            # タスクに関連するキーワードを抽出
            keywords = await self.breakdown_agent.extract_keywords(
                state["task_description"]
            )

            logger.info("\n" + "─" * 80)
            logger.info("📍 [フェーズ 2/3] コードベース分析")
            logger.info("─" * 80)

            # 賢くコードを読み込む（tree-sitter + ripgrep）
            code_content = analyzer.read_code_intelligently(
                keywords, max_functions=20, max_chars=50000
            )

            logger.info("\n" + "─" * 80)
            logger.info("📍 [フェーズ 3/3] タスク分解実行")
            logger.info("─" * 80)

            repo_context = f"""
# Project Structure
{file_tree}

# Project Summary
{summary}

# Related Code
{code_content if code_content else "No relevant code files found."}
"""

            subtasks = await self.breakdown_agent.break_down(
                state["task_description"], repo_context
            )

            state["subtasks"] = subtasks

            logger.info("\n" + "=" * 80)
            logger.info(f"✅ [ワークフロー] タスク分解完了: {len(subtasks)} 個のサブタスクを作成")
            logger.info("=" * 80)

        except Exception as e:
            state["error"] = f"Breakdown failed: {str(e)}"
            logger.error(state["error"], exc_info=True)

        return state

    async def _create_issues(self, state: WorkflowState) -> WorkflowState:
        """GitHub Issuesを作成"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("📝 [ワークフロー] GitHub Issues作成フェーズ開始")
            logger.info("=" * 80)
            logger.info(f"🎯 作成予定: {len(state['subtasks'])} 個のIssue")
            github = GitHubClient()
            created_issues = []

            # Repository ID、Project ID、およびフィールド情報を取得
            from src.github.queries import (
                GET_REPOSITORY_AND_PROJECT_IDS,
                GET_PROJECT_FIELDS,
            )

            ids_result = await github.execute_query(
                GET_REPOSITORY_AND_PROJECT_IDS,
                {
                    "org": settings.GITHUB_ORG,
                    "repo": settings.GITHUB_REPO,
                    "projectNumber": settings.GITHUB_PROJECT_NUMBER,
                },
            )

            repo_id = ids_result["repository"]["id"]
            project_id = ids_result["user"]["projectV2"]["id"]

            # Sizeフィールド情報を取得
            fields_result = await github.execute_query(
                GET_PROJECT_FIELDS,
                {
                    "org": settings.GITHUB_ORG,
                    "projectNumber": settings.GITHUB_PROJECT_NUMBER,
                },
            )

            # Sizeフィールドを探す
            size_field = None
            for field in fields_result["user"]["projectV2"]["fields"]["nodes"]:
                if field.get("name") == "Size":
                    size_field = field
                    break

            if not size_field:
                logger.warning("Size field not found in project")

            # 各サブタスクをIssue化
            logger.info("\n" + "─" * 80)
            logger.info("🔧 各サブタスクをIssue化")
            logger.info("─" * 80)

            for i, subtask in enumerate(state["subtasks"], 1):
                logger.info(f"\n📌 [{i}/{len(state['subtasks'])}] {subtask['title']}")
                # 参考コードセクションを構築
                reference_section = ""
                if subtask.get("reference_code"):
                    ref = subtask["reference_code"]
                    reference_section = f"""

## Reference Code
**File**: `{ref.get("file_path", "")}`

```python
{ref.get("snippet", "")}
```

**Note**: {ref.get("explanation", "")}
"""

                # Issue作成
                issue_body = f"""
## Description
{subtask["description"]}

## Acceptance Criteria
{chr(10).join(f"- [ ] {criterion}" for criterion in subtask.get("acceptance_criteria", []))}

## Estimated Effort
{subtask.get("estimated_effort", "M")}

## Dependencies
{chr(10).join(f"- {dep}" for dep in subtask.get("dependencies", []))}
{reference_section}
---
Created by AI Task Bot
"""

                # CREATE_ISSUE mutation実行
                issue_result = await github.execute_query(
                    CREATE_ISSUE,
                    {
                        "repositoryId": repo_id,
                        "title": subtask["title"],
                        "body": issue_body,
                    },
                )

                issue_id = issue_result["createIssue"]["issue"]["id"]
                issue_url = issue_result["createIssue"]["issue"]["url"]

                # Projectに追加
                project_item_result = await github.execute_query(
                    ADD_TO_PROJECT, {"projectId": project_id, "contentId": issue_id}
                )

                project_item_id = project_item_result["addProjectV2ItemById"]["item"][
                    "id"
                ]

                # Sizeフィールドを更新
                if size_field:
                    from src.utils.size_converter import (
                        convert_effort_to_size,
                        get_size_option_id,
                    )

                    estimated_effort = subtask.get("estimated_effort", "M")
                    size_value = convert_effort_to_size(estimated_effort)
                    size_option_id = get_size_option_id(
                        size_field["options"], size_value
                    )

                    if size_option_id:
                        await github.execute_query(
                            UPDATE_PROJECT_FIELD,
                            {
                                "projectId": project_id,
                                "itemId": project_item_id,
                                "fieldId": size_field["id"],
                                "value": {"singleSelectOptionId": size_option_id},
                            },
                        )
                        logger.info(
                            f"   ✓ Sizeフィールド設定: {estimated_effort} → {size_value}"
                        )
                    else:
                        logger.warning(f"   ⚠️ Sizeオプション {size_value} が見つかりません")

                created_issues.append({"title": subtask["title"], "url": issue_url})

                logger.info(f"   ✓ Issue作成完了: {issue_url}")

            state["created_issues"] = created_issues

            logger.info("\n" + "=" * 80)
            logger.info(f"✅ [ワークフロー] 全Issue作成完了: {len(created_issues)} 個")
            logger.info("=" * 80)
            for i, issue in enumerate(created_issues, 1):
                logger.info(f"   {i}. {issue['title']}")
                logger.info(f"      {issue['url']}")

        except Exception as e:
            state["error"] = f"Issue creation failed: {str(e)}"
            logger.error(state["error"], exc_info=True)

        return state

    async def execute(
        self, task_description: str, repo_url: str, timeout_seconds: int = 300
    ) -> WorkflowState:
        """ワークフローを実行

        Args:
            task_description: タスクの説明
            repo_url: リポジトリURL
            timeout_seconds: タイムアウト時間（秒）

        Returns:
            WorkflowState: 実行結果
        """
        initial_state = WorkflowState(
            task_description=task_description,
            repo_url=repo_url,
            repo_path=None,
            is_implemented=False,
            confidence=0.0,
            subtasks=[],
            created_issues=[],
            error="",
        )

        try:
            result = await asyncio.wait_for(
                self.workflow.ainvoke(initial_state), timeout=timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Workflow timeout after {timeout_seconds}s")
            initial_state["error"] = "Workflow timeout"
            return initial_state
