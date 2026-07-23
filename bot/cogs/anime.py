"""核心动漫系统模块 [🌐 公开 + 🔒 私密]。

功能：
- /anime   动漫百科查询（海报、评分、简介、声优）  [🌐]
- /season  季度新番速览                            [🌐]
- 「加入追番」按钮（Ephemeral 私密添加）            [🔒]
- /recommend AI 漫荒推荐（读取私密追番列表分析口味）[🔒]

注意：番剧数据一律来自 AniList API（services/anilist_service.py），
严禁让本地 Gemma 模型凭记忆回答番剧信息。
"""

import discord
from discord import app_commands
from discord.ext import commands

from services import ai_client, anilist_service


class AnimeCog(commands.Cog, name="Anime"):
    """动漫查询与追番管理。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="anime", description="查询动漫百科信息")
    async def anime(
        self, interaction: discord.Interaction, title: str
    ) -> None:
        """动漫百科查询 [🌐 公开]。"""
        # TODO(实现): anilist_service.search_anime(title) → embeds.render
        pass

    @app_commands.command(name="season", description="查看当前季度热门新番")
    async def season(self, interaction: discord.Interaction) -> None:
        """季度新番速览 [🌐 公开]。"""
        # TODO(实现): anilist_service.get_current_season() → embeds.render
        pass

    @app_commands.command(name="recommend", description="AI 漫荒推荐（私密）")
    async def recommend(self, interaction: discord.Interaction) -> None:
        """AI 漫荒推荐 [🔒 私密，Ephemeral]。"""
        # TODO(实现):
        # 1. 读取该用户的私密追番列表
        # 2. 让 AI 仅做「口味分析」，候选番剧数据必须来自 AniList
        # 3. 以 ephemeral=True 回复
        pass


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(AnimeCog(bot))
