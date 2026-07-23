"""Embed 渲染工具。

把服务层返回的原始数据渲染为 Discord Embed 卡片，
保持 Cogs 代码干净、展示逻辑集中管理。
"""

import discord


def render_anime_card(anime: dict) -> discord.Embed:
    """渲染动漫百科卡片（海报、评分、简介、声优）。

    Args:
        anime: AniList 返回的动漫信息 dict。

    Returns:
        Discord Embed 对象。
    """
    title = anime.get("title", {})
    romaji = title.get("romaji", "Unknown")
    english = title.get("english", "")
    native = title.get("native", "")

    # 标题优先级：romaji > english > native
    display_title = romaji or english or native

    # 评分
    score = anime.get("averageScore")
    score_text = f"⭐ {score}/100" if score else "暂无评分"

    # 简介（截取前 200 字符）
    description = anime.get("description", "暂无简介")
    if len(description) > 200:
        description = description[:200] + "..."

    # 集数与状态
    episodes = anime.get("episodes", "?")
    status = anime.get("status", "Unknown")
    status_map = {
        "FINISHED": "已完结",
        "RELEASING": "连载中",
        "NOT_YET_RELEASED": "未播出",
        "CANCELLED": "已取消",
    }
    status_text = status_map.get(status, status)

    # 创建 Embed
    embed = discord.Embed(
        title=display_title,
        description=description,
        color=discord.Color.blue(),
    )

    # 海报
    cover_image = anime.get("coverImage", {})
    if cover_image.get("large"):
        embed.set_thumbnail(url=cover_image["large"])

    # 字段
    embed.add_field(name="评分", value=score_text, inline=True)
    embed.add_field(name="集数", value=f"{episodes} 集", inline=True)
    embed.add_field(name="状态", value=status_text, inline=True)

    # 声优（如果有）
    characters = anime.get("characters", {}).get("nodes", [])
    if characters:
        char_names = [c.get("name", {}).get("full", "") for c in characters[:3]]
        embed.add_field(
            name="主要角色",
            value="\n".join(char_names),
            inline=False,
        )

    return embed


def render_season_list(animes: list[dict]) -> discord.Embed:
    """渲染季度新番列表。

    Args:
        animes: AniList 返回的新番列表。

    Returns:
        Discord Embed 对象。
    """
    embed = discord.Embed(
        title="📺 当前季度热门新番",
        color=discord.Color.green(),
    )

    for i, anime in enumerate(animes[:10], 1):
        title = anime.get("title", {})
        romaji = title.get("romaji", "Unknown")
        score = anime.get("averageScore")
        score_text = f"⭐ {score}/100" if score else "暂无评分"

        embed.add_field(
            name=f"{i}. {romaji}",
            value=score_text,
            inline=False,
        )

    return embed


def render_agenda(events: list[dict]) -> discord.Embed:
    """渲染个人日程列表。

    Args:
        events: 日历事件列表。

    Returns:
        Discord Embed 对象。
    """
    embed = discord.Embed(
        title="📅 我的日程",
        color=discord.Color.purple(),
    )

    for event in events:
        title = event.get("title", "无标题")
        start_time = event.get("start_time", "")
        # 简单格式化时间（截取前 16 字符）
        time_text = start_time[:16].replace("T", " ") if start_time else "未知时间"

        embed.add_field(
            name=title,
            value=f"🕐 {time_text}",
            inline=False,
        )

    return embed
