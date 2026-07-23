"""「加入追番」按钮视图 [🔒 私密]。

在动漫查询结果的 Embed 下方挂载按钮，
点击后通过 Ephemeral 隐藏回复悄悄写入个人追番列表，群里不留痕。
"""

import discord

from services import watchlist_service  # TODO(实现): services/watchlist_service.py


class WatchlistButton(discord.ui.Button):
    """加入追番按钮。"""

    def __init__(self, anime_id: int) -> None:
        super().__init__(
            label="加入追番",
            style=discord.ButtonStyle.primary,
            emoji="📌",
        )
        self.anime_id = anime_id

    async def callback(self, interaction: discord.Interaction) -> None:
        """点击回调：Ephemeral 私密确认。"""
        # TODO(实现):
        # await watchlist_service.add(interaction.user.id, self.anime_id)
        # await interaction.response.send_message(
        #     "已悄悄加入你的追番列表 ✅", ephemeral=True
        # )
        pass


class AnimeCardView(discord.ui.View):
    """动漫卡片视图：携带「加入追番」按钮。"""

    def __init__(self, anime_id: int) -> None:
        super().__init__(timeout=300)
        self.add_item(WatchlistButton(anime_id))
