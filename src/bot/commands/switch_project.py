import discord
from discord import app_commands
from src.github.client import GitHubClient
from src.github.queries import GET_REPOSITORY_AND_PROJECT_IDS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_switch_project_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/switch-projectコマンドをセットアップ"""

    @tree.command(
        name="switch-project",
        description="使用するGitHub Projectを切り替え"
    )
    @app_commands.describe(
        project_number="GitHub Projectの番号"
    )
    async def switch_project(
        interaction: discord.Interaction,
        project_number: int
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # プロジェクト番号の検証
            if project_number < 1:
                await interaction.followup.send(
                    "プロジェクト番号は1以上の整数を指定してください",
                    ephemeral=True
                )
                return

            # プロジェクトの存在確認
            client = GitHubClient()
            try:
                project_data = await client.execute_query(
                    GET_REPOSITORY_AND_PROJECT_IDS,
                    {
                        "org": settings.GITHUB_ORG,
                        "repo": settings.GITHUB_REPO,
                        "projectNumber": project_number,
                    }
                )

                # projectV2がNoneの場合、プロジェクトが存在しない
                if project_data["user"]["projectV2"] is None:
                    await interaction.followup.send(
                        f"プロジェクト番号 {project_number} が見つかりません",
                        ephemeral=True
                    )
                    return

                project_title = project_data["user"]["projectV2"]["title"]
            except Exception as e:
                await interaction.followup.send(
                    f"プロジェクトの確認中にエラーが発生しました\n"
                    f"エラー: {str(e)}",
                    ephemeral=True
                )
                return

            # ユーザーのプロジェクトを設定
            discord_id = str(interaction.user.id)
            project_manager.set_project(discord_id, project_number)

            embed = discord.Embed(
                title="✅ プロジェクト切り替え完了",
                description=f"プロジェクト番号 **{project_number}** に切り替えました",
                color=discord.Color.green()
            )

            embed.add_field(
                name="プロジェクト名",
                value=project_title,
                inline=False
            )

            embed.add_field(
                name="対象リポジトリ",
                value=f"{settings.GITHUB_ORG}/{settings.GITHUB_REPO}",
                inline=False
            )

            embed.add_field(
                name="次のステップ",
                value=(
                    "以降のコマンド実行時は、このプロジェクトが使用されます\n"
                    "`/current-project` で現在の設定を確認できます"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(
                f"switch-project executed by {interaction.user.name}: "
                f"switched to project #{project_number} ({project_title})"
            )

        except Exception as e:
            logger.error(f"Error in switch-project: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)


async def setup_current_project_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/current-projectコマンドをセットアップ"""

    @tree.command(
        name="current-project",
        description="現在使用しているGitHub Projectを表示"
    )
    async def current_project(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            discord_id = str(interaction.user.id)
            project_number = project_manager.get_project_number(discord_id)

            # プロジェクト情報を取得
            client = GitHubClient()
            try:
                project_data = await client.execute_query(
                    GET_REPOSITORY_AND_PROJECT_IDS,
                    {
                        "org": settings.GITHUB_ORG,
                        "repo": settings.GITHUB_REPO,
                        "projectNumber": project_number,
                    }
                )

                # projectV2がNoneの場合、プロジェクトが存在しない
                if project_data["user"]["projectV2"] is None:
                    await interaction.followup.send(
                        f"プロジェクト番号 {project_number} が見つかりません",
                        ephemeral=True
                    )
                    return

                project_title = project_data["user"]["projectV2"]["title"]
                is_default = project_number == settings.GITHUB_PROJECT_NUMBER
            except Exception as e:
                await interaction.followup.send(
                    f"プロジェクト情報の取得に失敗しました\n"
                    f"エラー: {str(e)}",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="📋 現在のプロジェクト設定",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="プロジェクト番号",
                value=f"**{project_number}**" + (" (デフォルト)" if is_default else ""),
                inline=False
            )

            embed.add_field(
                name="プロジェクト名",
                value=project_title,
                inline=False
            )

            embed.add_field(
                name="対象リポジトリ",
                value=f"{settings.GITHUB_ORG}/{settings.GITHUB_REPO}",
                inline=False
            )

            if not is_default:
                embed.add_field(
                    name="ヒント",
                    value="`/switch-project` で別のプロジェクトに切り替えできます",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(
                f"current-project executed by {interaction.user.name}: "
                f"project #{project_number} ({project_title})"
            )

        except Exception as e:
            logger.error(f"Error in current-project: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}", ephemeral=True)
