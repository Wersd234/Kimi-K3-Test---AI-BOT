"""日程与生活管理模块 [🔒 私密]。

功能：
- /remind  自然语言日历管理（AI Function Calling 提取时间与事项）
- /agenda  查看个人日程（Ephemeral）
- 到点后由 core/scheduler 触发私信提醒（不在本模块内）
"""

import discord
from discord import app_commands
from discord.ext import commands

from services import ai_client, calendar_service


class ScheduleCog(commands.Cog, name="Schedule"):
    """日程与生活管理。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="remind", description="自然语言创建提醒（私密）")
    async def remind(
        self, interaction: discord.Interaction, text: str
    ) -> None:
        """例：「明天下午3点提醒我开会」[🔒 私密，Ephemeral]。

        AI 仅负责意图抽取（Function Calling），
        事件落库由 services/calendar_service 完成。
        """
        # TODO(实现):
        # 1. ai_client.extract_schedule_intent(text) → 结构化事件
        # 2. calendar_service.add_event() 入库
        # 3. ephemeral 确认回复
        pass

    @app_commands.command(name="agenda", description="查看我的日程（私密）")
    async def agenda(self, interaction: discord.Interaction) -> None:
        """查看未来日程 [🔒 私密，Ephemeral]。"""
        # TODO(实现): calendar_service.list_upcoming() → ephemeral 回复
        pass


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(ScheduleCog(bot))
