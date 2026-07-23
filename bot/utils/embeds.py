"""Embed 渲染工具。

把服务层返回的原始数据渲染为 Discord Embed 卡片，
保持 Cogs 代码干净、展示逻辑集中管理。
"""

import discord


def render_anime_card(anime: dict) -> discord.Embed:
    """渲染动漫百科卡片（海报、评分、简介、声优）。"""
    # TODO(实现): 从 anilist_service 返回的 dict 构建 Embed
    raise NotImplementedError


def render_season_list(animes: list[dict]) -> discord.Embed:
    """渲染季度新番列表。"""
    # TODO(实现)
    raise NotImplementedError


def render_agenda(events: list[dict]) -> discord.Embed:
    """渲染个人日程列表。"""
    # TODO(实现)
    raise NotImplementedError
