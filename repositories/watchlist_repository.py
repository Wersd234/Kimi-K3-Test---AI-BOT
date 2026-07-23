"""watchlist 表仓储：私人追番列表。

所有方法为类方法（@classmethod），无需实例化即可调用。
"""

from repositories.base import BaseRepository


class WatchlistRepository(BaseRepository):
    """封装 watchlist 表的全部 SQL 操作。"""

    @classmethod
    async def add(
        cls, user_id: int, anime_id: int, anime_title: str
    ) -> bool:
        """加入追番列表。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。
            anime_title: 番剧标题（冗余存储，减少 API 调用）。

        Returns:
            True 表示新添加，False 表示已存在（UNIQUE 约束忽略）。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO watchlist
                (user_id, anime_id, anime_title)
            VALUES (?, ?, ?)
            """,
            (user_id, anime_id, anime_title),
        )
        await db.commit()
        return cursor.rowcount > 0

    @classmethod
    async def remove(cls, user_id: int, anime_id: int) -> bool:
        """从追番列表移除。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            True 表示删除成功，False 表示未找到。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            DELETE FROM watchlist
            WHERE user_id = ? AND anime_id = ?
            """,
            (user_id, anime_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    @classmethod
    async def list_by_user(cls, user_id: int) -> list[dict]:
        """读取用户的完整追番列表。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            [{"anime_id": 1, "anime_title": "...", "last_notified_episode": 12, ...}, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT anime_id, anime_title, last_notified_episode, added_at
            FROM watchlist
            WHERE user_id = ?
            ORDER BY added_at DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @classmethod
    async def list_all_anime_ids(cls) -> list[int]:
        """全库去重的被追踪番剧 ID（供更新轮询批量查询）。

        Returns:
            [1, 2, 3, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            "SELECT DISTINCT anime_id FROM watchlist"
        )
        rows = await cursor.fetchall()
        return [row["anime_id"] for row in rows]

    @classmethod
    async def list_users_tracking(cls, anime_id: int) -> list[int]:
        """查出追踪某部番的所有用户（新集数发布时要 Ping 的人）。

        Args:
            anime_id: AniList 媒体 ID。

        Returns:
            [user_id1, user_id2, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT user_id FROM watchlist
            WHERE anime_id = ?
            """,
            (anime_id,),
        )
        rows = await cursor.fetchall()
        return [row["user_id"] for row in rows]

    @classmethod
    async def get_last_notified_episode(
        cls, user_id: int, anime_id: int
    ) -> int | None:
        """读取某用户对某番上次已提醒的集数。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            集数，或 None（从未提醒）。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT last_notified_episode FROM watchlist
            WHERE user_id = ? AND anime_id = ?
            """,
            (user_id, anime_id),
        )
        row = await cursor.fetchone()
        return row["last_notified_episode"] if row else None

    @classmethod
    async def set_last_notified_episode(
        cls, user_id: int, anime_id: int, episode: int
    ) -> None:
        """更新已提醒集数（防止重复 Ping）。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。
            episode: 最新已提醒的集数。
        """
        db = cls.get_db()
        await db.execute(
            """
            UPDATE watchlist
            SET last_notified_episode = ?
            WHERE user_id = ? AND anime_id = ?
            """,
            (episode, user_id, anime_id),
        )
        await db.commit()

    @classmethod
    async def is_tracking(cls, user_id: int, anime_id: int) -> bool:
        """检查用户是否已追踪某部番。

        Args:
            user_id: Discord 用户 ID。
            anime_id: AniList 媒体 ID。

        Returns:
            True 表示已追踪，False 表示未追踪。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT 1 FROM watchlist
            WHERE user_id = ? AND anime_id = ?
            LIMIT 1
            """,
            (user_id, anime_id),
        )
        return await cursor.fetchone() is not None
