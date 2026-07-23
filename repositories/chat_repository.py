"""chat_history 表仓储：短期对话上下文。

GRASP 原则：
- Information Expert: 本类拥有 chat_history 表的全部知识
- Single Responsibility: 只负责 chat_history 表的 CRUD
"""

from repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    """封装 chat_history 表的全部 SQL 操作。"""

    async def get_recent(self, user_id: int, limit: int) -> list[dict]:
        """读取用户最近 N 轮对话（按时间升序返回）。

        Args:
            user_id: Discord 用户 ID。
            limit: 最多返回的对话轮数。

        Returns:
            对话列表，每项包含 role 和 content。
            按时间正序排列，以匹配 OpenAI messages 的上下文顺序。
        """
        cursor = await self._db.execute(
            """
            SELECT role, content
            FROM (
                SELECT role, content, id
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

    async def append(self, user_id: int, role: str, content: str) -> None:
        """追加一轮对话记录。

        Args:
            user_id: Discord 用户 ID。
            role: 角色（"user" 或 "assistant"）。
            content: 对话内容。
        """
        await self._db.execute(
            """
            INSERT INTO chat_history (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content),
        )
        await self._db.commit()

    async def trim_to_limit(self, user_id: int, limit: int) -> None:
        """裁剪历史，仅保留最近 N 条。

        Args:
            user_id: Discord 用户 ID。
            limit: 保留的最大条数。

        设计说明：
            防止表无限膨胀，保持查询性能。
        """
        await self._db.execute(
            """
            DELETE FROM chat_history
            WHERE user_id = ?
              AND id NOT IN (
                  SELECT id
                  FROM chat_history
                  WHERE user_id = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (user_id, user_id, limit),
        )
        await self._db.commit()
