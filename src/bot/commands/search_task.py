import discord
from discord import app_commands
from typing import Optional
from src.github.client import GitHubClient
from src.github.queries import GET_PROJECT_ITEMS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_search_task_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/search-taskコマンドをセットアップ"""

    @tree.command(
        name="search-task",
        description="タスクを検索・フィルタリング"
    )
    @app_commands.describe(
        keyword="タイトルに含まれるキーワード",
        status="ステータスでフィルタ（例: Todo, In Progress, Done）",
        assignee="担当者でフィルタ（GitHub ID）",
        state="Issueの状態でフィルタ（OPEN または CLOSED）"
    )
    async def search_task(
        interaction: discord.Interaction,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        state: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            if not any([keyword, status, assignee, state]):
                await interaction.followup.send(
                    "少なくとも1つの検索条件を指定してください",
                    ephemeral=True
                )
                return

            # stateのバリデーション
            if state and state.upper() not in ["OPEN", "CLOSED"]:
                await interaction.followup.send(
                    "state は OPEN または CLOSED を指定してください",
                    ephemeral=True
                )
                return

            # ユーザーのプロジェクト番号を取得
            discord_id = str(interaction.user.id)
            project_number = project_manager.get_project_number(discord_id)

            client = GitHubClient()
            variables = {
                "org": settings.GITHUB_ORG,
                "projectNumber": project_number,
            }

            data = await client.execute_query(GET_PROJECT_ITEMS, variables)
            project = data["user"]["projectV2"]

            # タスクをフィルタリング
            filtered_tasks = []
            for item in project["items"]["nodes"]:
                if not item["content"]:  # Draft itemはスキップ
                    continue

                issue_data = item["content"]

                # キーワードフィルタ
                if keyword:
                    if keyword.lower() not in issue_data["title"].lower():
                        continue

                # ステータスフィルタ
                if status:
                    item_status = None
                    for field_value in item["fieldValues"]["nodes"]:
                        if field_value and "field" in field_value:
                            field_name = field_value["field"]["name"]
                            if field_name == "Status":
                                item_status = field_value["name"]
                                break

                    if not item_status or item_status.lower() != status.lower():
                        continue

                # 担当者フィルタ
                if assignee:
                    assignee_logins = [a["login"] for a in issue_data["assignees"]["nodes"]]
                    if assignee.lower() not in [a.lower() for a in assignee_logins]:
                        continue

                # stateフィルタ
                if state:
                    if issue_data.get("state", "").upper() != state.upper():
                        continue

                # フィルタを通過したタスクを追加
                task_status = "未設定"
                for field_value in item["fieldValues"]["nodes"]:
                    if field_value and "field" in field_value:
                        field_name = field_value["field"]["name"]
                        if field_name == "Status":
                            task_status = field_value["name"]
                            break

                filtered_tasks.append({
                    "title": issue_data["title"],
                    "url": issue_data["url"],
                    "number": issue_data["number"],
                    "status": task_status,
                    "state": issue_data.get("state", "UNKNOWN"),
                    "assignees": [a["login"] for a in issue_data["assignees"]["nodes"]],
                })

            # 検索条件を整形
            search_conditions = []
            if keyword:
                search_conditions.append(f"キーワード: `{keyword}`")
            if status:
                search_conditions.append(f"ステータス: `{status}`")
            if assignee:
                search_conditions.append(f"担当者: `@{assignee}`")
            if state:
                search_conditions.append(f"状態: `{state}`")

            # Embedメッセージを作成
            embed = discord.Embed(
                title="🔍 タスク検索結果",
                description=f"**検索条件**:\n{chr(10).join(search_conditions)}\n\n**結果**: {len(filtered_tasks)}件",
                color=discord.Color.blue(),
            )

            if len(filtered_tasks) == 0:
                embed.add_field(
                    name="検索結果なし",
                    value="条件に一致するタスクが見つかりませんでした",
                    inline=False
                )
            else:
                for task in filtered_tasks[:25]:  # Discordの制限: 25 fields max
                    assignees_str = ", ".join(task["assignees"]) if task["assignees"] else "未割当"
                    state_emoji = "🟢" if task["state"] == "OPEN" else "🔴"

                    embed.add_field(
                        name=f"{state_emoji} #{task['number']} {task['title']}",
                        value=f"**Status**: {task['status']}\n**担当**: {assignees_str}\n[View]({task['url']})",
                        inline=False,
                    )

                if len(filtered_tasks) > 25:
                    embed.set_footer(
                        text=f"注: 最初の25件のみ表示。残り{len(filtered_tasks) - 25}件"
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"search-task executed by {interaction.user.name}: {search_conditions}")

        except Exception as e:
            logger.error(f"Error in search-task: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)
