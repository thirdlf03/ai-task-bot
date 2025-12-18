import asyncio
from src.bot.client import TaskBot
from src.bot.commands.get_all_task import setup_get_all_task_command
from src.bot.commands.get_task import setup_get_task_command
from src.bot.commands.create_task import setup_create_task_command
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """メインエントリーポイント"""
    bot = TaskBot()

    # コマンド登録
    await setup_get_all_task_command(bot.tree)  # Phase 1
    await setup_get_task_command(bot.tree)  # Phase 1
    await setup_create_task_command(bot.tree)  # Phase 3

    logger.info("Starting AI Task Bot...")
    logger.info(
        f"Target Project: {settings.GITHUB_ORG}/{settings.GITHUB_REPO} "
        f"(Project #{settings.GITHUB_PROJECT_NUMBER})"
    )
    logger.info("All commands registered: /get-all-task, /get-task, /create-task")

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
