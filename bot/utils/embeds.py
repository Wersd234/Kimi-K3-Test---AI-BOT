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
    native = title.get("native", "")
    romaji = title.get("romaji", "")
    english = title.get("english", "")

    # 标题优先级：native（中文）> romaji > english
    display_title = native or romaji or english or "Unknown"

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
    """渲染季度新番列表（优化排版）。

    Args:
        animes: AniList 返回的新番列表。

    Returns:
        Discord Embed 对象。
    """
    embed = discord.Embed(
        title="📺 当前季度热门新番",
        description="以下是本季度最受欢迎的新番：",
        color=discord.Color.green(),
    )

    # 每行显示 2 部番剧
    for i in range(0, len(animes), 2):
        # 左侧番剧
        left = animes[i]
        left_title = left.get("title", {}).get("native") or left.get("title", {}).get("romaji", "Unknown")
        left_score = left.get("averageScore")
        left_score_text = f"⭐ {left_score}" if left_score else "暂无评分"
        left_text = f"**{left_title}**\n{left_score_text}"

        # 右侧番剧（如果存在）
        if i + 1 < len(animes):
            right = animes[i + 1]
            right_title = right.get("title", {}).get("native") or right.get("title", {}).get("romaji", "Unknown")
            right_score = right.get("averageScore")
            right_score_text = f"⭐ {right_score}" if right_score else "暂无评分"
            right_text = f"**{right_title}**\n{right_score_text}"

            embed.add_field(name=left_text, value=right_text, inline=True)
        else:
            embed.add_field(name=left_text, value="\u200b", inline=True)

    return embed


def render_agenda(events: list[dict]) -> discord.Embed:
    """渲染个人日程列表（转换为用户本地时区）。

    Args:
        events: 日历事件列表。

    Returns:
        Discord Embed 对象。
    """
    from datetime import datetime

    embed = discord.Embed(
        title="📅 我的日程",
        color=discord.Color.purple(),
    )

    for event in events:
        title = event.get("title", "无标题")
        start_time_str = event.get("start_time", "")

        # 解析 ISO 8601 时间并转换为本地时区
        try:
            start_time = datetime.fromisoformat(start_time_str)
            local_time = start_time.astimezone()
            time_text = local_time.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_text = start_time_str[:16].replace("T", " ")

        embed.add_field(
            name=title,
            value=f"🕐 {time_text}",
            inline=False,
        )

    return embed
