import discord
from discord import app_commands
from typing import Optional
from src.github.client import GitHubClient
from src.github.queries import GET_ISSUE_WITH_PROJECT_ITEM, GET_PROJECT_FIELDS, GET_USER_ID
from src.github.mutations import UPDATE_PROJECT_FIELD, ADD_ASSIGNEES, REMOVE_ASSIGNEES
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_update_task_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/update-taskコマンドをセットアップ"""

    @tree.command(
        name="update-task",
        description="タスクのステータスや担当者を更新"
    )
    @app_commands.describe(
        issue_number="Issue番号",
        status="新しいステータス（例: Todo, In Progress, Done）",
        assign="担当者として追加するGitHub ID",
        unassign="担当者から削除するGitHub ID"
    )
    async def update_task(
        interaction: discord.Interaction,
        issue_number: int,
        status: Optional[str] = None,
        assign: Optional[str] = None,
        unassign: Optional[str] = None
    ):
        await interaction.response.defer()

        try:
            if not status and not assign and not unassign:
                await interaction.followup.send(
                    "少なくとも1つのパラメータ（status, assign, unassign）を指定してください"
                )
                return

            # ユーザーのプロジェクト番号を取得
            discord_id = str(interaction.user.id)
            project_number = project_manager.get_project_number(discord_id)

            client = GitHubClient()

            # Issue情報を取得
            issue_data = await client.execute_query(
                GET_ISSUE_WITH_PROJECT_ITEM,
                {
                    "org": settings.GITHUB_ORG,
                    "repo": settings.GITHUB_REPO,
                    "issueNumber": issue_number,
                    "projectNumber": project_number
                }
            )

            issue = issue_data["repository"]["issue"]
            if not issue:
                await interaction.followup.send(f"Issue #{issue_number} が見つかりません")
                return

            # 該当するProject Itemを取得
            project_item = None
            for item in issue["projectItems"]["nodes"]:
                if item["project"]["number"] == project_number:
                    project_item = item
                    break

            if not project_item:
                await interaction.followup.send(
                    f"Issue #{issue_number} はプロジェクトに追加されていません"
                )
                return

            updates = []

            # ステータス更新
            if status:
                fields_data = await client.execute_query(
                    GET_PROJECT_FIELDS,
                    {
                        "org": settings.GITHUB_ORG,
                        "projectNumber": project_number
                    }
                )

                status_field = None
                for field in fields_data["user"]["projectV2"]["fields"]["nodes"]:
                    if field.get("name") == "Status":
                        status_field = field
                        break

                if not status_field:
                    await interaction.followup.send("プロジェクトにStatusフィールドが見つかりません")
                    return

                # ステータスオプションを検索
                status_option_id = None
                for option in status_field["options"]:
                    if option["name"].lower() == status.lower():
                        status_option_id = option["id"]
                        break

                if not status_option_id:
                    available_statuses = [opt["name"] for opt in status_field["options"]]
                    await interaction.followup.send(
                        f"ステータス '{status}' が見つかりません。利用可能なステータス: {', '.join(available_statuses)}"
                    )
                    return

                # ステータス更新実行
                await client.execute_query(
                    UPDATE_PROJECT_FIELD,
                    {
                        "projectId": project_item["project"]["id"],
                        "itemId": project_item["id"],
                        "fieldId": status_field["id"],
                        "value": {"singleSelectOptionId": status_option_id}
                    }
                )
                updates.append(f"Status → {status}")

            # 担当者追加
            if assign:
                user_data = await client.execute_query(
                    GET_USER_ID,
                    {"login": assign}
                )

                if not user_data.get("user"):
                    await interaction.followup.send(f"GitHub ユーザー '{assign}' が見つかりません")
                    return

                user_id = user_data["user"]["id"]

                await client.execute_query(
                    ADD_ASSIGNEES,
                    {
                        "issueId": issue["id"],
                        "assigneeIds": [user_id]
                    }
                )
                updates.append(f"担当者追加: @{assign}")

            # 担当者削除
            if unassign:
                user_data = await client.execute_query(
                    GET_USER_ID,
                    {"login": unassign}
                )

                if not user_data.get("user"):
                    await interaction.followup.send(f"GitHub ユーザー '{unassign}' が見つかりません")
                    return

                user_id = user_data["user"]["id"]

                await client.execute_query(
                    REMOVE_ASSIGNEES,
                    {
                        "issueId": issue["id"],
                        "assigneeIds": [user_id]
                    }
                )
                updates.append(f"担当者削除: @{unassign}")

            # 結果を表示
            embed = discord.Embed(
                title=f"タスク更新完了 #{issue_number}",
                description=f"**{issue['title']}**",
                color=discord.Color.green(),
                url=issue["url"]
            )

            embed.add_field(
                name="更新内容",
                value="\n".join(f"✓ {update}" for update in updates),
                inline=False
            )

            await interaction.followup.send(embed=embed)
            logger.info(f"update-task executed by {interaction.user.name} for issue #{issue_number}")

        except Exception as e:
            logger.error(f"Error in update-task: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}")
