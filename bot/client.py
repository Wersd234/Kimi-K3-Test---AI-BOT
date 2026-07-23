"""Discord Bot 客户端定义（Factory Method + 依赖注入）。

职责：
- 接收组合根注入的 Config（显式依赖，不读全局状态）
- 加载所有 Cogs（指令模块）
- 同步斜杠指令树
- 不包含任何 AI / 数据库业务逻辑
"""

import logging

import discord
from discord.ext import commands

from core.config import Config

logger = logging.getLogger(__name__)

# 需要加载的 Cog 模块列表
COGS = [
    "bot.cogs.ai_chat",
    "bot.cogs.anime",
    "bot.cogs.schedule",
    "bot.cogs.persona",
]


class ButlerBot(commands.Bot):
    """二次元私人管家 Bot 客户端。"""

    def __init__(self, config: Config) -> None:
        """注入配置并声明所需 Intents。

        Args:
            config: 全局配置（用于读取 dev_guild_id 等）。
        """
        intents = discord.Intents.default()
        intents.message_content = True  # 读取消息内容以响应 @ 对话
        intents.members = True          # 感知在线状态（护肝提醒）
        super().__init__(command_prefix="!", intents=intents)
        self._config = config

    async def setup_hook(self) -> None:
        """启动钩子：加载 Cogs 并同步指令树。"""
        for cog in COGS:
            await self.load_extension(cog)
        logger.info("已加载 %d 个 Cog", len(COGS))

        # 开发期：仅同步到指定服务器（即时生效）；留空则全局同步
        if self._config.dev_guild_id:
            guild = discord.Object(id=self._config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("指令已同步至开发服务器 %s", self._config.dev_guild_id)
        else:
            await self.tree.sync()
            logger.info("指令已全局同步")

    async def on_ready(self) -> None:
        """Bot 就绪回调。"""
        logger.info("✅ 已登录：%s (ID: %s)", self.user, self.user.id)


def create_bot(config: Config) -> ButlerBot:
    """工厂方法：创建并返回 Bot 实例。

    Args:
        config: 由组合根注入的全局配置。
    """
    return ButlerBot(config)
