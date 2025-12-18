import discord
from discord import app_commands
from src.github.client import GitHubClient
from src.github.queries import GET_USER_TASKS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.user_mapping import UserMapping

logger = get_logger(__name__)


async def setup_my_tasks_command(tree: app_commands.CommandTree, user_mapping: UserMapping):
    """/my-tasksコマンドをセットアップ"""

    @tree.command(
        name="my-tasks",
        description="自分のタスクを表示"
    )
    @app_commands.describe(
        github_id="GitHub ID（省略時はマッピング設定から取得）"
    )
    async def my_tasks(
        interaction: discord.Interaction,
        github_id: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # GitHub IDを決定
            if not github_id:
                discord_id = str(interaction.user.id)
                github_id = user_mapping.get_github_id(discord_id)

                if not github_id:
                    await interaction.followup.send(
                        "GitHub IDが設定されていません。\n"
                        "以下のいずれかの方法で設定してください:\n"
                        "1. `/link-github <GitHub ID>` コマンドで設定\n"
                        "2. `/my-tasks <GitHub ID>` で直接指定",
                        ephemeral=True
                    )
                    return

            client = GitHubClient()
            variables = {
                "login": github_id,
                "org": settings.GITHUB_ORG,
                "projectNumber": settings.GITHUB_PROJECT_NUMBER,
            }

            data = await client.execute_query(GET_USER_TASKS, variables)

            if not data["targetUser"]:
                await interaction.followup.send(
                    f"ユーザー `{github_id}` が見つかりません",
                    ephemeral=True
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
                        == settings.GITHUB_PROJECT_NUMBER
                    ):
                        project_tasks.append(issue)
                        break

            # Embedメッセージを作成
            embed = discord.Embed(
                title=f"📋 {github_id} のタスク一覧",
                description=f"{project['title']} - 全{len(project_tasks)}件",
                color=discord.Color.green(),
            )

            if len(project_tasks) == 0:
                embed.add_field(
                    name="タスクなし",
                    value="割り当てられているタスクはありません",
                    inline=False
                )
            else:
                for task in project_tasks[:25]:
                    state_emoji = "🟢" if task["state"] == "OPEN" else "🔴"
                    embed.add_field(
                        name=f"{state_emoji} #{task['number']} {task['title']}",
                        value=f"**Repo**: {task['repository']['nameWithOwner']}\n**State**: {task['state']}\n[View]({task['url']})",
                        inline=False,
                    )

                if len(project_tasks) > 25:
                    embed.set_footer(
                        text=f"注: 最初の25件のみ表示。残り{len(project_tasks) - 25}件"
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"my-tasks executed by {interaction.user.name} for GitHub ID {github_id}")

        except Exception as e:
            logger.error(f"Error in my-tasks: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)


async def setup_link_github_command(tree: app_commands.CommandTree, user_mapping: UserMapping):
    """/link-githubコマンドをセットアップ"""

    @tree.command(
        name="link-github",
        description="Discord IDとGitHub IDを紐付け"
    )
    @app_commands.describe(
        github_id="GitHub ID"
    )
    async def link_github(
        interaction: discord.Interaction,
        github_id: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # GitHub IDの存在確認
            client = GitHubClient()
            from src.github.queries import GET_USER_ID

            user_data = await client.execute_query(
                GET_USER_ID,
                {"login": github_id}
            )

            if not user_data.get("user"):
                await interaction.followup.send(
                    f"GitHub ユーザー '{github_id}' が見つかりません",
                    ephemeral=True
                )
                return

            # マッピングを設定
            discord_id = str(interaction.user.id)
            user_mapping.set_mapping(discord_id, github_id)

            embed = discord.Embed(
                title="✅ GitHub ID紐付け完了",
                description=f"Discord ID `{interaction.user.name}` と GitHub ID `{github_id}` を紐付けました",
                color=discord.Color.green()
            )

            embed.add_field(
                name="次のステップ",
                value="`/my-tasks` コマンドで自分のタスクを確認できます",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"link-github executed by {interaction.user.name}: {discord_id} -> {github_id}")

        except Exception as e:
            logger.error(f"Error in link-github: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)
