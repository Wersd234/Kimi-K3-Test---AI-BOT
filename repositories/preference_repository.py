"""preferences 表仓储：长期偏好记忆（RAG 条目）。

GRASP 原则：
- Information Expert: 本类拥有 preferences 表的全部知识
- Single Responsibility: 只负责 preferences 表的 CRUD
"""

from repositories.base import BaseRepository


class PreferenceRepository(BaseRepository):
    """封装 preferences 表的全部 SQL 操作。"""

    async def list_all(self, user_id: int) -> list[str]:
        """读取用户的全部长期偏好条目。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            偏好内容列表（按时间倒序）。
        """
        cursor = await self._db.execute(
            """
            SELECT content
            FROM preferences
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [row["content"] for row in rows]

    async def add(self, user_id: int, content: str) -> None:
        """写入一条长期偏好。

        Args:
            user_id: Discord 用户 ID。
            content: 偏好内容（如「讨厌下雨」「喜欢机甲番」）。
        """
        await self._db.execute(
            """
            INSERT INTO preferences (user_id, content)
            VALUES (?, ?)
            """,
            (user_id, content),
        )
        await self._db.commit()

    async def delete(self, user_id: int, content: str) -> int:
        """删除匹配内容的偏好条目。

        Args:
            user_id: Discord 用户 ID。
            content: 要删除的偏好内容。

        Returns:
            受影响的行数（删除的条目数）。
        """
        cursor = await self._db.execute(
            """
            DELETE FROM preferences
            WHERE user_id = ? AND content = ?
            """,
            (user_id, content),
        )
        await self._db.commit()
        return cursor.rowcount
