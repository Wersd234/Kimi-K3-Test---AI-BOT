"""核心动漫系统模块 [🌐 公开 + 🔒 私密]。

功能：
- /anime   动漫百科查询（海报、评分、简介、声优）  [🌐]
- /season  季度新番速览                            [🌐]
- /recommend AI 漫荒推荐（读取私密追番列表分析口味）[🔒]
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import embeds

logger = logging.getLogger(__name__)


class AnimeCog(commands.Cog, name="Anime"):
    """动漫查询与追番管理。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="anime", description="查询动漫百科信息")
    @app_commands.describe(title="番剧名称（支持中文/日文/英文）")
    async def anime(
        self, interaction: discord.Interaction, title: str
    ) -> None:
        """动漫百科查询 [🌐 公开]。"""
        await interaction.response.defer()

        try:
            bangumi = self.bot.services.bangumi_service  # 使用 Bangumi
            anime = await bangumi.search_anime(title)

            if not anime:
                await interaction.followup.send(
                    f"抱歉，没有找到《{title}》的相关信息..."
                )
                return

            embed = embeds.render_anime_card(anime)
            await interaction.followup.send(embed=embed)

        except Exception as exc:
            logger.error("动漫查询失败: %s", exc)
            await interaction.followup.send("查询失败，请稍后再试...")

    @app_commands.command(name="season", description="查看当前季度热门新番")
    async def season(self, interaction: discord.Interaction) -> None:
        """季度新番速览 [🌐 公开]。"""
        await interaction.response.defer()

        try:
            bangumi = self.bot.services.bangumi_service  # 使用 Bangumi
            animes = await bangumi.get_current_season(page=1)

            if not animes:
                await interaction.followup.send("抱歉，获取新番列表失败...")
                return

            embed = embeds.render_season_list(animes)
            await interaction.followup.send(embed=embed)

        except Exception as exc:
            logger.error("季度新番查询失败: %s", exc)
            await interaction.followup.send("查询失败，请稍后再试...")

    @app_commands.command(name="recommend", description="AI 漫荒推荐（私密）")
    async def recommend(self, interaction: discord.Interaction) -> None:
        """AI 漫荒推荐 [🔒 私密，Ephemeral]。"""
        await interaction.response.defer(ephemeral=True)

        try:
            # TODO(实现): 读取追番列表 → AI 口味分析 → Bangumi 候选 → 推荐
            await interaction.followup.send(
                "AI 漫荒推荐功能尚未实现，敬请期待..."
            )

        except Exception as exc:
            logger.error("AI 漫荒推荐失败: %s", exc)
            await interaction.followup.send("推荐失败，请稍后再试...")


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(AnimeCog(bot))
