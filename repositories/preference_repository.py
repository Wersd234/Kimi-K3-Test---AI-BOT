"""preferences 表仓储：长期偏好记忆（RAG 条目）。

所有方法为类方法（@classmethod），无需实例化即可调用。
"""

from repositories.base import BaseRepository


class PreferenceRepository(BaseRepository):
    """封装 preferences 表的全部 SQL 操作。"""

    @classmethod
    async def add(cls, user_id: int, content: str) -> None:
        """写入一条长期偏好。

        Args:
            user_id: Discord 用户 ID。
            content: 偏好内容（如「讨厌下雨」「喜欢机甲番」）。
        """
        db = cls.get_db()
        await db.execute(
            """
            INSERT INTO preferences (user_id, content)
            VALUES (?, ?)
            """,
            (user_id, content),
        )
        await db.commit()

    @classmethod
    async def list(cls, user_id: int) -> list[str]:
        """读取用户全部长期偏好。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            ["讨厌下雨", "喜欢机甲番", ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT content FROM preferences
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [row["content"] for row in rows]

    @classmethod
    async def exists(cls, user_id: int, content: str) -> bool:
        """检查偏好是否已存在（用于去重）。

        Args:
            user_id: Discord 用户 ID。
            content: 偏好内容。

        Returns:
            True 表示已存在，False 表示不存在。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT 1 FROM preferences
            WHERE user_id = ? AND content = ?
            LIMIT 1
            """,
            (user_id, content),
        )
        return await cursor.fetchone() is not None

    @classmethod
    async def remove(cls, user_id: int, content: str) -> bool:
        """删除一条偏好。

        Args:
            user_id: Discord 用户 ID。
            content: 偏好内容。

        Returns:
            True 表示删除成功，False 表示未找到。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            DELETE FROM preferences
            WHERE user_id = ? AND content = ?
            """,
            (user_id, content),
        )
        await db.commit()
        return cursor.rowcount > 0

    @classmethod
    async def clear(cls, user_id: int) -> None:
        """清空用户的全部偏好。

        Args:
            user_id: Discord 用户 ID。
        """
        db = cls.get_db()
        await db.execute(
            "DELETE FROM preferences WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
