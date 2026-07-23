"""Discord 交互组件（按钮、表单等 View）。"""

import discord


class SeasonPaginationView(discord.ui.View):
    """季度新番翻页视图（周一到周日，共 7 页）。"""

    def __init__(self, animes_by_day: dict[int, list[dict]], timeout: int = 180):
        """初始化翻页视图。

        Args:
            animes_by_day: 按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
                          0=周一, 6=周日
            timeout: 超时时间（秒）。
        """
        super().__init__(timeout=timeout)
        self.animes_by_day = animes_by_day
        self.current_page = 0  # 当前页码（0=周一）
        self.day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 更新按钮状态
        self._update_buttons()

    def _update_buttons(self) -> None:
        """更新按钮状态（禁用/启用）。"""
        # 上一页按钮
        self.previous_button.disabled = self.current_page == 0
        # 下一页按钮
        self.next_button.disabled = self.current_page == 6

    def _render_page(self) -> discord.Embed:
        """渲染当前页的 Embed。

        Returns:
            Discord Embed 对象。
        """
        day_name = self.day_names[self.current_page]
        animes = self.animes_by_day.get(self.current_page, [])

        embed = discord.Embed(
            title=f"📺 当前季度热门新番 - {day_name}",
            description=f"以下是{day_name}更新的热门新番：",
            color=discord.Color.green(),
        )

        if not animes:
            embed.add_field(
                name="暂无新番",
                value=f"{day_name}没有更新的新番。",
                inline=False,
            )
        else:
            # 显示 top 10
            for i, anime in enumerate(animes[:10], 1):
                title = anime.get("title", {}).get("native", "Unknown")
                score = anime.get("averageScore")
                score_text = f"⭐ {score}/100" if score else "暂无评分"

                # 更新时间（如果有）
                air_time = anime.get("air_time", "未知时间")

                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"{score_text} | 🕐 {air_time}",
                    inline=False,
                )

        # 页码指示
        embed.set_footer(text=f"第 {self.current_page + 1}/7 页")

        return embed

    @discord.ui.button(label="◀️ 上一页", style=discord.ButtonStyle.primary)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """上一页按钮回调。"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            embed = self._render_page()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ 下一页", style=discord.ButtonStyle.primary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """下一页按钮回调。"""
        if self.current_page < 6:
            self.current_page += 1
            self._update_buttons()
            embed = self._render_page()
            await interaction.response.edit_message(embed=embed, view=self)
