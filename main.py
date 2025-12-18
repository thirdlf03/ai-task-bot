import asyncio
from src.bot.client import TaskBot
from src.bot.commands.get_all_task import setup_get_all_task_command
from src.bot.commands.get_task import setup_get_task_command
from src.bot.commands.create_task import setup_create_task_command
from src.bot.commands.update_task import setup_update_task_command
from src.bot.commands.stats import setup_stats_command
from src.bot.commands.my_tasks import setup_my_tasks_command, setup_link_github_command
from src.bot.commands.search_task import setup_search_task_command
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """メインエントリーポイント"""
    bot = TaskBot()

    # コマンド登録
    await setup_get_all_task_command(bot.tree)  # 全タスク取得
    await setup_get_task_command(bot.tree)  # ユーザータスク取得
    await setup_create_task_command(bot.tree)  # タスク作成
    await setup_update_task_command(bot.tree)  # タスク更新
    await setup_stats_command(bot.tree)  # 統計情報
    await setup_my_tasks_command(bot.tree, bot.user_mapping)  # 自分のタスク
    await setup_link_github_command(bot.tree, bot.user_mapping)  # GitHub ID紐付け
    await setup_search_task_command(bot.tree)  # タスク検索

    logger.info("Starting AI Task Bot...")
    logger.info(
        f"Target Project: {settings.GITHUB_ORG}/{settings.GITHUB_REPO} "
        f"(Project #{settings.GITHUB_PROJECT_NUMBER})"
    )
    logger.info(
        "All commands registered: "
        "/get-all-task, /get-task, /create-task, "
        "/update-task, /stats, /my-tasks, /link-github, /search-task"
    )

    try:
        await bot.start(settings.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        await bot.close()
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped")
