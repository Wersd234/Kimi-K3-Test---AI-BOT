"""watchlist 表仓储：私人追番列表。

GRASP 原则：
- Information Expert: 本类拥有 watchlist 表的全部知识
- Single Responsibility: 只负责 watchlist 表的 CRUD
"""

from repositories.base import BaseRepository


class WatchlistRepository(BaseRepository):
    """封装 watchlist 表的全部 SQL 操作。"""

    async def add(
        self,
        user_id: int,
        anime_id: int,
        anime_title: str,
    ) -> bool:
        """加入追番列表，已存在则忽略。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。
            anime_title: 番剧标题（冗余存储，减少 API 调用）。

        Returns:
            True 表示新加入，False 表示已存在。
        """
        cursor = await self._db.execute(
            """
            INSERT OR IGNORE INTO watchlist (user_id, anime_id, anime_title)
            VALUES (?, ?, ?)
            """,
            (user_id, anime_id, anime_title),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def remove(self, user_id: int, anime_id: int) -> bool:
        """从追番列表移除。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            True 表示移除成功，False 表示本就不在列表中。
        """
        cursor = await self._db.execute(
            """
            DELETE FROM watchlist
            WHERE user_id = ? AND anime_id = ?
            """,
            (user_id, anime_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_by_user(self, user_id: int) -> list[dict]:
        """读取用户的完整追番列表。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            追番列表，每项包含 anime_id, anime_title, added_at。
        """
        cursor = await self._db.execute(
            """
            SELECT anime_id, anime_title, added_at
            FROM watchlist
            WHERE user_id = ?
            ORDER BY added_at DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def list_distinct_anime(self) -> list[int]:
        """返回全库所有被追踪的 anime_id。

        Returns:
            去重后的 anime_id 列表。

        设计说明：
            轮询更新时只需查询每个唯一的 anime_id，
            避免重复调用 AniList API。
        """
        cursor = await self._db.execute(
            "SELECT DISTINCT anime_id FROM watchlist",
        )
        rows = await cursor.fetchall()
        return [row["anime_id"] for row in rows]

    async def list_users_by_anime(self, anime_id: int) -> list[int]:
        """返回追踪了某部番剧的全部用户。

        Args:
            anime_id: AniList 媒体 ID。

        Returns:
            用户 ID 列表，用于定向 Ping 提醒。
        """
        cursor = await self._db.execute(
            "SELECT user_id FROM watchlist WHERE anime_id = ?",
            (anime_id,),
        )
        rows = await cursor.fetchall()
        return [row["user_id"] for row in rows]
