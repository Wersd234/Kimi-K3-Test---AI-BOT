"""chat_history 表仓储：短期对话上下文。

所有方法为类方法（@classmethod），无需实例化即可调用。
"""

from repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    """封装 chat_history 表的全部 SQL 操作。"""

    @classmethod
    async def append(cls, user_id: int, role: str, content: str) -> None:
        """追加一条对话记录。

        Args:
            user_id: Discord 用户 ID。
            role: 角色（'user' / 'assistant' / 'system'）。
            content: 消息内容。
        """
        db = cls.get_db()
        await db.execute(
            """
            INSERT INTO chat_history (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content),
        )
        await db.commit()

    @classmethod
    async def get_recent(
        cls, user_id: int, limit: int = 20
    ) -> list[dict]:
        """读取最近 limit 条对话记录（按时间正序）。

        算法：内层子查询先取最新 N 条（DESC），外层再翻转回正序，
        保证结果可直接拼入 OpenAI messages 数组。

        Args:
            user_id: Discord 用户 ID。
            limit: 返回的最大条数（默认 20）。

        Returns:
            [{"role": "user", "content": "...", "created_at": "..."}, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT role, content, created_at FROM (
                SELECT id, role, content, created_at
                FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @classmethod
    async def trim(cls, user_id: int, keep: int) -> None:
        """裁剪历史，仅保留最近 keep 条（防止表无限膨胀）。

        Args:
            user_id: Discord 用户 ID。
            keep: 保留的最大条数。
        """
        db = cls.get_db()
        await db.execute(
            """
            DELETE FROM chat_history
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (user_id, user_id, keep),
        )
        await db.commit()

    @classmethod
    async def clear(cls, user_id: int) -> None:
        """清空用户的全部对话历史。

        Args:
            user_id: Discord 用户 ID。
        """
        db = cls.get_db()
        await db.execute(
            "DELETE FROM chat_history WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
