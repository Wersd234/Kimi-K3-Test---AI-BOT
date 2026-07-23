"""追番列表服务 [🔒 私密]。

管理用户的私人 Watchlist：入库、移除、查询，
并配合 AniList API 与调度器实现新集数更新 Ping 提醒。
"""

import logging

from repositories import WatchlistRepository

logger = logging.getLogger(__name__)


class WatchlistService:
    """追番业务逻辑（依赖注入 WatchlistRepository）。"""

    async def add(self, user_id: int, anime_id: int, anime_title: str) -> bool:
        """把一部番剧悄悄加入用户的私人追番列表。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。
            anime_title: 番剧标题。

        Returns:
            True 表示新添加，False 表示已存在。
        """
        added = await WatchlistRepository.add(user_id, anime_id, anime_title)
        if added:
            logger.info(
                "用户 %s 添加追番: %s (id: %d)",
                user_id,
                anime_title,
                anime_id,
            )
        return added

    async def remove(self, user_id: int, anime_id: int) -> bool:
        """从追番列表移除。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            True 表示删除成功，False 表示未找到。
        """
        removed = await WatchlistRepository.remove(user_id, anime_id)
        if removed:
            logger.info("用户 %s 移除追番: %d", user_id, anime_id)
        return removed

    async def list_watchlist(self, user_id: int) -> list[dict]:
        """读取用户的完整追番列表。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            追番列表（按添加时间倒序）。
        """
        watchlist = await WatchlistRepository.list_by_user(user_id)
        logger.info("用户 %s 查询追番列表: %d 部", user_id, len(watchlist))
        return watchlist

    async def is_tracking(self, user_id: int, anime_id: int) -> bool:
        """检查用户是否已追踪某部番。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            True 表示已追踪，False 表示未追踪。
        """
        return await WatchlistRepository.is_tracking(user_id, anime_id)

    async def get_all_tracked_anime(self) -> list[int]:
        """返回全库所有被追踪的 anime_id（供更新轮询去重查询）。

        Returns:
            anime_id 列表。
        """
        anime_ids = await WatchlistRepository.list_all_anime_ids()
        logger.info("全库共有 %d 部被追踪的番剧", len(anime_ids))
        return anime_ids

    async def list_users_tracking(self, anime_id: int) -> list[int]:
        """查出追踪某部番的所有用户（新集数发布时要 Ping 的人）。

        Args:
            anime_id: AniList 媒体 ID。

        Returns:
            user_id 列表。
        """
        users = await WatchlistRepository.list_users_tracking(anime_id)
        logger.info("番剧 %d 有 %d 个用户追踪", anime_id, len(users))
        return users

    async def get_last_notified_episode(
        self, user_id: int, anime_id: int
    ) -> int | None:
        """读取某用户对某番上次已提醒的集数。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            集数，或 None（从未提醒）。
        """
        return await WatchlistRepository.get_last_notified_episode(
            user_id, anime_id
        )

    async def set_last_notified_episode(
        self, user_id: int, anime_id: int, episode: int
    ) -> None:
        """更新已提醒集数（防止重复 Ping）。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。
            episode: 最新已提醒的集数。
        """
        await WatchlistRepository.set_last_notified_episode(
            user_id, anime_id, episode
        )
        logger.info(
            "用户 %s 的番剧 %d 已更新提醒集数: %d",
            user_id,
            anime_id,
            episode,
        )
