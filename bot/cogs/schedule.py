"""日程与生活管理模块 [🔒 私密]。

功能：
- /remind  自然语言日历管理（AI Function Calling 提取时间与事项）
- /agenda  查看个人日程（Ephemeral）
"""

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import embeds

logger = logging.getLogger(__name__)


class ScheduleCog(commands.Cog, name="Schedule"):
    """日程与生活管理。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="remind", description="自然语言创建提醒（私密）")
    @app_commands.describe(text="例如：明天下午3点提醒我开会")
    async def remind(
        self, interaction: discord.Interaction, text: str
    ) -> None:
        """例：「明天下午3点提醒我开会」[🔒 私密，Ephemeral]。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # TODO(实现): AI Function Calling 提取时间与事项
            # 目前先简单解析（示例）
            calendar = self.bot.services.calendar_service

            # 示例：1 小时后提醒
            start_time = datetime.now(timezone.utc) + timedelta(hours=1)
            event_id = await calendar.add_event(
                interaction.user.id,
                text,
                start_time.isoformat(),
                remind_before_minutes=0,
            )

            await interaction.followup.send(
                f"已创建提醒：{text}\n"
                f"时间：{start_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"（AI 自然语言解析功能尚未实现，目前默认为 1 小时后）"
            )

        except Exception as exc:
            logger.error("创建提醒失败: %s", exc)
            await interaction.followup.send("创建提醒失败，请稍后再试...")

    @app_commands.command(name="agenda", description="查看我的日程（私密）")
    async def agenda(self, interaction: discord.Interaction) -> None:
        """查看未来日程 [🔒 私密，Ephemeral]。"""
        await interaction.response.defer(ephemeral=True)

        try:
            calendar = self.bot.services.calendar_service
            events = await calendar.list_upcoming(interaction.user.id, limit=10)

            if not events:
                await interaction.followup.send("你目前没有即将到来的日程。")
                return

            embed = embeds.render_agenda(events)
            await interaction.followup.send(embed=embed)

        except Exception as exc:
            logger.error("查询日程失败: %s", exc)
            await interaction.followup.send("查询失败，请稍后再试...")


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(ScheduleCog(bot))
