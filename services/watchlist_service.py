"""追番列表服务 [🔒 私密]。

管理用户的私人 Watchlist：入库、移除、查询，
并配合 AniList API 与调度器实现新集数更新 Ping 提醒。

TODO(依赖注入): 实现时改为接收 WatchlistRepository 参数。
"""

# TODO(实现): 待实现时改为依赖注入模式
# from repositories import WatchlistRepository


async def add(user_id: int, anime_id: int) -> None:
    """把一部番剧悄悄加入用户的私人追番列表。"""
    # TODO(实现): 调用 WatchlistRepository.add()
    raise NotImplementedError


async def remove(user_id: int, anime_id: int) -> None:
    """从追番列表移除一部番剧。"""
    # TODO(实现): 调用 WatchlistRepository.remove()
    raise NotImplementedError


async def list_watchlist(user_id: int) -> list[dict]:
    """读取用户的完整追番列表（供 AI 漫荒推荐分析口味）。"""
    # TODO(实现): 调用 WatchlistRepository.list_by_user()
    raise NotImplementedError


async def get_all_tracked_anime() -> list[int]:
    """返回全库所有被追踪的 anime_id（供更新轮询去重查询）。"""
    # TODO(实现): 调用 WatchlistRepository.list_all_anime_ids()
    raise NotImplementedError
