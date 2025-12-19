import discord
from discord import app_commands
from src.github.client import GitHubClient
from src.github.queries import GET_USER_TASKS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_get_task_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/ get-taskコマンドをセットアップ"""

    @tree.command(
        name="get-task", description="指定したGitHub IDのユーザーのタスクを取得"
    )
    @app_commands.describe(github_id="GitHub ユーザーID")
    async def get_task(interaction: discord.Interaction, github_id: str):
        await interaction.response.defer()

        try:
            # ユーザーのプロジェクト番号を取得
            discord_id = str(interaction.user.id)
            project_number = project_manager.get_project_number(discord_id)

            client = GitHubClient()
            variables = {
                "login": github_id,
                "org": settings.GITHUB_ORG,
                "projectNumber": project_number,
            }

            data = await client.execute_query(GET_USER_TASKS, variables)

            if not data["targetUser"]:
                await interaction.followup.send(
                    f"ユーザー `{github_id}` が見つかりません"
                )
                return

            project = data["orgUser"]["projectV2"]
            user_issues = data["targetUser"]["issues"]["nodes"]

            # このProjectに属するIssueのみフィルタ
            project_tasks = []
            for issue in user_issues:
                for project_item in issue["projectItems"]["nodes"]:
                    if (
                        project_item["project"]["number"]
                        == project_number
                    ):
                        project_tasks.append(issue)
                        break

            # Embedメッセージを作成
            embed = discord.Embed(
                title=f"📋 {github_id} のタスク一覧",
                description=f"{project['title']} - 全{len(project_tasks)}件",
                color=discord.Color.green(),
            )

            for task in project_tasks[:25]:
                embed.add_field(
                    name=f"#{task['number']} {task['title']}",
                    value=f"**Repo**: {task['repository']['nameWithOwner']}\n**State**: {task['state']}\n[View]({task['url']})",
                    inline=False,
                )

            if len(project_tasks) > 25:
                embed.set_footer(
                    text=f"注: 最初の25件のみ表示。残り{len(project_tasks) - 25}件"
                )

            await interaction.followup.send(embed=embed)
            logger.info(f"get-task executed for user {github_id}")

        except Exception as e:
            logger.error(f"Error in get-task: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}")
