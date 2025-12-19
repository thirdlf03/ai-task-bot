import discord
from discord import app_commands
from src.config import settings
from src.utils.logger import get_logger
from src.utils.user_mapping import UserMapping
from src.utils.project_manager import ProjectManager

logger = get_logger(__name__)


class TaskBot(discord.Client):
    """AI Task Bot Discord クライアント"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.user_mapping = UserMapping()
        self.project_manager = ProjectManager()

    async def setup_hook(self):
        """スラッシュコマンドを登録"""
        guild = discord.Object(id=settings.DISCORD_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info(f"Commands synced to guild {settings.DISCORD_GUILD_ID}")

    async def on_ready(self):
        """Bot起動時の処理"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")
