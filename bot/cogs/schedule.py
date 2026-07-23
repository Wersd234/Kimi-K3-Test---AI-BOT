"""日程与生活管理模块 [🔒 私密]。

功能：
- /remind  自然语言日历管理（AI Function Calling 提取时间与事项）
- /agenda  查看个人日程（Ephemeral）
"""

import logging
import re
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

    def _parse_time(self, text: str) -> datetime:
        """简单解析自然语言时间（中文）。

        支持：
        - X 分钟后
        - X 小时后
        - 明天/后天 + X 点
        - 今天下午 X 点

        Args:
            text: 用户输入文本。

        Returns:
            解析后的 datetime（UTC）。
        """
        now = datetime.now(timezone.utc)

        # X 分钟后
        match = re.search(r"(\d+)\s*分钟后", text)
        if match:
            minutes = int(match.group(1))
            return now + timedelta(minutes=minutes)

        # X 小时后
        match = re.search(r"(\d+)\s*小时后", text)
        if match:
            hours = int(match.group(1))
            return now + timedelta(hours=hours)

        # 明天/后天 + X 点
        match = re.search(r"(明天|后天)\s*(\d+)\s*点", text)
        if match:
            day_offset = 1 if match.group(1) == "明天" else 2
            hour = int(match.group(2))
            target = now + timedelta(days=day_offset)
            return target.replace(hour=hour, minute=0, second=0, microsecond=0)

        # 今天下午 X 点
        match = re.search(r"今天下午\s*(\d+)\s*点", text)
        if match:
            hour = int(match.group(1))
            return now.replace(hour=hour, minute=0, second=0, microsecond=0)

        # 默认：1 小时后
        return now + timedelta(hours=1)

    @app_commands.command(name="remind", description="自然语言创建提醒（私密）")
    @app_commands.describe(text="例如：明天下午3点提醒我开会")
    async def remind(
        self, interaction: discord.Interaction, text: str
    ) -> None:
        """例：「明天下午3点提醒我开会」[🔒 私密，Ephemeral]。"""
        await interaction.response.defer(ephemeral=True)

        try:
            calendar = self.bot.services.calendar_service

            # 解析时间
            start_time = self._parse_time(text)

            # 提取事件标题（移除时间相关词汇）
            title = re.sub(r"\d+\s*(分钟后|小时后|点)", "", text)
            title = re.sub(r"(明天|后天|今天下午)", "", title).strip()
            if not title:
                title = text

            event_id = await calendar.add_event(
                interaction.user.id,
                title,
                start_time.isoformat(),
                remind_before_minutes=0,
            )

            # 转换为用户本地时区显示
            local_time = start_time.astimezone()
            time_str = local_time.strftime("%Y-%m-%d %H:%M")

            await interaction.followup.send(
                f"已创建提醒：{title}\n"
                f"时间：{time_str}"
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
