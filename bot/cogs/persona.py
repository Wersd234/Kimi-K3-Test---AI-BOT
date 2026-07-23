"""专属人设设定模块 [🔒 私密]。

功能：
- /persona 设定管家对自己的专属称呼（如「主人」「大小姐」）
- /bedtime 设定作息时间（用于护肝防熬夜提醒）

所有回复均为 Ephemeral（仅触发用户可见），保护隐私。
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from services import memory

logger = logging.getLogger(__name__)


class PersonaCog(commands.Cog, name="Persona"):
    """用户专属设定。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="persona",
        description="设定管家对你的专属称呼（私密）",
    )
    @app_commands.describe(
        honorific="管家对你的称呼，如：主人、大小姐、前辈",
    )
    async def persona(
        self, interaction: discord.Interaction, honorific: str
    ) -> None:
        """设定专属称呼 [🔒 私密，Ephemeral]。"""
        try:
            await memory.set_honorific(interaction.user.id, honorific)
            await interaction.response.send_message(
                f"好的，以后我就称呼你为「{honorific}」了 ✨",
                ephemeral=True,
            )
            logger.info(
                "用户 %s 设定称呼为「%s」",
                interaction.user.id,
                honorific,
            )
        except ValueError as exc:
            await interaction.response.send_message(
                f"设定失败：{exc}",
                ephemeral=True,
            )

    @app_commands.command(
        name="bedtime",
        description="设定作息时间，管家会在深夜提醒你休息（私密）",
    )
    @app_commands.describe(
        time="作息时间，格式 HH:MM，如 23:30",
    )
    async def bedtime(
        self, interaction: discord.Interaction, time: str
    ) -> None:
        """设定作息时间 [🔒 私密，Ephemeral]。"""
        try:
            await memory.set_bedtime(interaction.user.id, time)
            await interaction.response.send_message(
                f"已记录你的作息时间：{time}。"
                "深夜还在线的话，我会来催你休息的 🌙",
                ephemeral=True,
            )
            logger.info(
                "用户 %s 设定作息时间为 %s",
                interaction.user.id,
                time,
            )
        except memory.InvalidBedtimeError as exc:
            await interaction.response.send_message(
                f"设定失败：{exc}",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(PersonaCog(bot))
