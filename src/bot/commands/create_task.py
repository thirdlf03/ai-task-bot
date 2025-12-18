import discord
from discord import app_commands
import re
from src.ai.workflow import CreateTaskWorkflow
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def validate_repo_url(url: str) -> bool:
    """リポジトリURLを検証

    Args:
        url: 検証するURL

    Returns:
        bool: URLが有効ならTrue
    """
    pattern = r"^https://github\.com/[\w-]+/[\w-]+(\.git)?$"
    return bool(re.match(pattern, url))


async def setup_create_task_command(tree: app_commands.CommandTree):
    """/create-taskコマンドをセットアップ"""

    @tree.command(
        name="create-task", description="AI AgentがタスクをGitHub Projectsに登録"
    )
    @app_commands.describe(
        task="実装したいタスクの内容", repo_url="リポジトリURL（省略時は設定値を使用）"
    )
    async def create_task(
        interaction: discord.Interaction, task: str, repo_url: str = None
    ):
        await interaction.response.defer()

        try:
            # 入力検証
            if len(task) > 2000:
                await interaction.followup.send(
                    "タスクの説明が長すぎます（2000文字以内）"
                )
                return

            # デフォルトのリポジトリURL
            if not repo_url:
                repo_url = f"https://github.com/{settings.GITHUB_ORG}/{settings.GITHUB_REPO}.git"
            elif not validate_repo_url(repo_url):
                await interaction.followup.send("無効なリポジトリURLです")
                return

            # 進行状況を表示
            await interaction.followup.send(
                f"タスク分析を開始します...\nタスク: `{task}`\nリポジトリ: {repo_url}"
            )

            # ワークフロー実行
            workflow = CreateTaskWorkflow()
            result = await workflow.execute(task, repo_url)

            # エラーチェック
            if result.get("error"):
                await interaction.followup.send(
                    f"エラーが発生しました: {result['error']}"
                )
                return

            # 実装済みの場合
            if result["is_implemented"]:
                embed = discord.Embed(
                    title="タスク既に実装済み",
                    description=f"このタスクは既に実装されている可能性があります（信頼度: {result['confidence']:.1%}）",
                    color=discord.Color.green(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Issue作成成功
            if result["created_issues"]:
                embed = discord.Embed(
                    title="タスク作成完了",
                    description=f"{len(result['created_issues'])}個のサブタスクを作成しました",
                    color=discord.Color.blue(),
                )

                for issue in result["created_issues"][:10]:  # 最大10件表示
                    embed.add_field(
                        name=issue["title"],
                        value=f"[View Issue]({issue['url']})",
                        inline=False,
                    )

                if len(result["created_issues"]) > 10:
                    embed.set_footer(
                        text=f"残り{len(result['created_issues']) - 10}件のIssue"
                    )

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"create-task executed by {interaction.user.name}: "
                    f"{len(result['created_issues'])} issues created"
                )
            else:
                await interaction.followup.send("タスクを分解できませんでした")

        except Exception as e:
            logger.error(f"Error in create-task: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}")
