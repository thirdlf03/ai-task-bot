import discord
from discord import app_commands
from src.github.client import GitHubClient
from src.github.queries import GET_PROJECT_ITEMS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_get_all_task_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/ get-all-taskコマンドをセットアップ"""

    @tree.command(
        name="get-all-task",
        description="GitHub Projectsのタスクを取得（完了タスク非表示）",
    )
    @app_commands.describe(show_done="完了タスクも表示する（デフォルト: false）")
    async def get_all_task(interaction: discord.Interaction, show_done: bool = False):
        await interaction.response.defer(ephemeral=True)  # 本人のみ表示

        try:
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
            tasks = []
            for item in project["items"]["nodes"]:
                if not item["content"]:  # Draft itemはスキップ
                    continue

                # Statusフィールドを取得
                status = None
                for field_value in item["fieldValues"]["nodes"]:
                    if field_value and "field" in field_value:
                        field_name = field_value["field"]["name"]
                        if field_name == "Status":
                            status = field_value["name"]
                            break

                # 完了タスクをフィルタ
                if not show_done and status == "Done":
                    continue

                issue_data = item["content"]
                tasks.append(
                    {
                        "title": issue_data["title"],
                        "url": issue_data["url"],
                        "number": issue_data["number"],
                        "status": status or "未設定",
                        "assignees": [
                            a["login"] for a in issue_data["assignees"]["nodes"]
                        ],
                    }
                )

            # Embedメッセージを作成
            embed = discord.Embed(
                title=f"📋 {project['title']} のタスク一覧",
                description=f"全{len(tasks)}件のタスク",
                color=discord.Color.blue(),
            )

            for task in tasks[:25]:  # Discordの制限: 25 fields max
                assignees = (
                    ", ".join(task["assignees"]) if task["assignees"] else "未割当"
                )
                embed.add_field(
                    name=f"#{task['number']} {task['title']}",
                    value=f"**Status**: {task['status']}\n**担当**: {assignees}\n[View]({task['url']})",
                    inline=False,
                )

            if len(tasks) > 25:
                embed.set_footer(
                    text=f"注: 最初の25件のみ表示。残り{len(tasks) - 25}件"
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"get-all-task executed by {interaction.user.name}")

        except Exception as e:
            logger.error(f"Error in get-all-task: {e}", exc_info=True)
            await interaction.followup.send(
                f"エラーが発生しました: {str(e)}", ephemeral=True
            )
