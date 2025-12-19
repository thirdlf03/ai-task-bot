import discord
from discord import app_commands
from collections import Counter
from src.github.client import GitHubClient
from src.github.queries import GET_PROJECT_ITEMS
from src.config import settings
from src.utils.logger import get_logger
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


async def setup_stats_command(tree: app_commands.CommandTree, project_manager: ProjectManager):
    """/statsコマンドをセットアップ"""

    @tree.command(
        name="stats",
        description="プロジェクトの進捗状況を表示"
    )
    async def stats(interaction: discord.Interaction):
        await interaction.response.defer()

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

            # 統計情報を収集
            total_tasks = 0
            status_count = Counter()
            assignee_count = Counter()
            size_count = Counter()
            state_count = Counter()

            for item in project["items"]["nodes"]:
                if not item["content"]:  # Draft itemはスキップ
                    continue

                total_tasks += 1
                issue_data = item["content"]

                # Issueのステート（OPEN/CLOSED）
                state_count[issue_data.get("state", "UNKNOWN")] += 1

                # フィールド値を取得
                for field_value in item["fieldValues"]["nodes"]:
                    if not field_value or "field" not in field_value:
                        continue

                    field_name = field_value["field"]["name"]

                    if field_name == "Status":
                        status_count[field_value["name"]] += 1
                    elif field_name == "Size":
                        size_count[field_value["name"]] += 1

                # 担当者
                for assignee in issue_data["assignees"]["nodes"]:
                    assignee_count[assignee["login"]] += 1

            # 統計がない場合の処理
            if total_tasks == 0:
                await interaction.followup.send("プロジェクトにタスクが見つかりません")
                return

            # 完了率を計算
            done_count = status_count.get("Done", 0)
            completion_rate = (done_count / total_tasks * 100) if total_tasks > 0 else 0

            # Embedメッセージを作成
            embed = discord.Embed(
                title=f"📊 {project['title']} - 統計情報",
                color=discord.Color.blue()
            )

            # 全体サマリー
            summary = f"""
**総タスク数**: {total_tasks}
**完了率**: {completion_rate:.1f}% ({done_count}/{total_tasks})
**Open**: {state_count.get('OPEN', 0)} | **Closed**: {state_count.get('CLOSED', 0)}
"""
            embed.add_field(name="📈 全体サマリー", value=summary.strip(), inline=False)

            # ステータス別
            if status_count:
                status_bars = []
                for status_name, count in status_count.most_common():
                    percentage = (count / total_tasks * 100)
                    bar_length = int(percentage / 5)  # 20文字がmax（100% / 5）
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    status_bars.append(f"**{status_name}**: {bar} {count} ({percentage:.1f}%)")

                embed.add_field(
                    name="📋 ステータス別",
                    value="\n".join(status_bars),
                    inline=False
                )

            # サイズ別
            if size_count:
                size_text = []
                for size_name, count in sorted(size_count.items()):
                    percentage = (count / total_tasks * 100)
                    size_text.append(f"**{size_name}**: {count} ({percentage:.1f}%)")

                embed.add_field(
                    name="📏 サイズ別",
                    value="\n".join(size_text),
                    inline=False
                )

            # 担当者別（上位5名）
            if assignee_count:
                assignee_text = []
                for assignee, count in assignee_count.most_common(5):
                    assignee_text.append(f"**@{assignee}**: {count}タスク")

                unassigned = total_tasks - sum(assignee_count.values())
                if unassigned > 0:
                    assignee_text.append(f"**未割当**: {unassigned}タスク")

                embed.add_field(
                    name="👥 担当者別（上位5名）",
                    value="\n".join(assignee_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="👥 担当者別",
                    value="すべてのタスクが未割当です",
                    inline=False
                )

            # フッター
            embed.set_footer(text=f"最終更新: {interaction.created_at.strftime('%Y-%m-%d %H:%M')}")

            await interaction.followup.send(embed=embed)
            logger.info(f"stats executed by {interaction.user.name}")

        except Exception as e:
            logger.error(f"Error in stats: {e}", exc_info=True)
            await interaction.followup.send(f"エラーが発生しました: {str(e)}")
