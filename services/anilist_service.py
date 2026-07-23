"""AniList GraphQL API 封装（真实动漫数据的唯一来源）。

提供：
- 动漫百科查询（海报、评分、简介、声优）
- 季度新番列表
- 追番更新检测（最新集数发布状态）

TODO(依赖注入): 实现时改为接收 Config 参数，而非读取全局配置。
"""

# TODO(实现): 待实现时改为依赖注入模式
# import aiohttp
# from core.config import Config


async def search_anime(title: str) -> dict | None:
    """按标题搜索动漫，返回百科信息。

    Args:
        title: 番剧名称（支持中文/日文/英文）。

    Returns:
        动漫信息 dict，未找到返回 None。
    """
    # TODO(实现): GraphQL query Media(search: $title, type: ANIME)
    raise NotImplementedError


async def get_current_season(page: int = 1) -> list[dict]:
    """获取当前季度热门新番列表。

    Args:
        page: 分页页码。

    Returns:
        新番信息 dict 列表。
    """
    # TODO(实现): GraphQL query 当前 season + seasonYear，按热度排序
    raise NotImplementedError


async def get_anime_status(anime_id: int) -> dict | None:
    """查询单部番剧的播出状态与最新集数（用于更新 Ping 轮询）。

    Args:
        anime_id: AniList 媒体 ID。

    Returns:
        包含 status / nextAiringEpisode 等字段的 dict。
    """
    # TODO(实现)
    raise NotImplementedError
