"""calendar_events 表仓储：日历事件与提醒。

GRASP 原则：
- Information Expert: 本类拥有 calendar_events 表的全部知识
- Single Responsibility: 只负责 calendar_events 表的 CRUD

核心算法：
- 数据库即队列：重启后从 SQLite 恢复扫描，绝不丢任务
- 提醒时刻 = start_time - remind_before 分钟
"""

from repositories.base import BaseRepository


class CalendarRepository(BaseRepository):
    """封装 calendar_events 表的全部 SQL 操作。"""

    async def add(
        self,
        user_id: int,
        title: str,
        start_time: str,
        remind_before_minutes: int,
    ) -> int:
        """创建日历事件。

        Args:
            user_id: Discord 用户 ID。
            title: 事件标题（如「开会」）。
            start_time: ISO 8601 格式起始时间（含时区）。
            remind_before_minutes: 提前多少分钟提醒。

        Returns:
            新事件的 rowid。
        """
        cursor = await self._db.execute(
            """
            INSERT INTO calendar_events
                (user_id, title, start_time, remind_before)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, start_time, remind_before_minutes),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def list_upcoming(
        self,
        user_id: int,
        limit: int,
    ) -> list[dict]:
        """列出用户未来的日程事件。

        Args:
            user_id: Discord 用户 ID。
            limit: 最多返回的事件数。

        Returns:
            事件列表，按时间升序排列。
        """
        cursor = await self._db.execute(
            """
            SELECT id, title, start_time, remind_before
            FROM calendar_events
            WHERE user_id = ? AND start_time >= datetime('now')
            ORDER BY start_time ASC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_due_events(self, now_iso: str) -> list[dict]:
        """取出所有到点待提醒的事件。

        Args:
            now_iso: 当前时间的 ISO 8601 格式字符串。

        Returns:
            到点事件列表，每项包含 id, user_id, title, start_time。

        核心算法（数据库即队列）：
            提醒时刻 = start_time - remind_before 分钟
            条件：reminded = 0 且 提醒时刻 <= now
        """
        cursor = await self._db.execute(
            """
            SELECT id, user_id, title, start_time
            FROM calendar_events
            WHERE reminded = 0
              AND datetime(start_time, '-' || remind_before || ' minutes')
                  <= ?
            ORDER BY start_time ASC
            """,
            (now_iso,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_reminded(self, event_id: int) -> None:
        """把事件标记为已提醒。

        Args:
            event_id: 事件 ID。

        设计说明：
            幂等操作，防止重复 DM。
        """
        await self._db.execute(
            """
            UPDATE calendar_events
            SET reminded = 1
            WHERE id = ?
            """,
            (event_id,),
        )
        await self._db.commit()

    async def delete(self, user_id: int, event_id: int) -> bool:
        """删除事件（仅限本人）。

        Args:
            user_id: Discord 用户 ID。
            event_id: 事件 ID。

        Returns:
            True 表示删除成功，False 表示事件不存在或不属于该用户。
        """
        cursor = await self._db.execute(
            """
            DELETE FROM calendar_events
            WHERE id = ? AND user_id = ?
            """,
            (event_id, user_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0
