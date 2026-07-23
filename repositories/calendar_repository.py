"""calendar_events 表仓储：日历事件与提醒。

所有方法为类方法（@classmethod），无需实例化即可调用。

时区说明：
- start_time 以 ISO 8601 字符串存储（含时区偏移，如 +10:00）。
- SQLite datetime() 会把带偏移的时间归一化为 UTC，
  因此「到点判断」与 UTC 的 datetime('now') 比较是时区安全的。
"""

from repositories.base import BaseRepository


class CalendarRepository(BaseRepository):
    """封装 calendar_events 表的全部 SQL 操作。"""

    @classmethod
    async def add(
        cls,
        user_id: int,
        title: str,
        start_time: str,
        remind_before: int = 0,
    ) -> int:
        """创建日历事件，返回新事件 id。

        Args:
            user_id: Discord 用户 ID。
            title: 事件标题（如「开会」）。
            start_time: ISO 8601 格式起始时间（含时区偏移）。
            remind_before: 提前多少分钟提醒（0 表示到点提醒）。

        Returns:
            新事件的 rowid。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            INSERT INTO calendar_events
                (user_id, title, start_time, remind_before)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, start_time, remind_before),
        )
        await db.commit()
        return cursor.lastrowid

    @classmethod
    async def list_upcoming(
        cls, user_id: int, now_iso: str, limit: int = 10
    ) -> list[dict]:
        """列出用户未来的日程事件（按时间升序）。

        Args:
            user_id: Discord 用户 ID。
            now_iso: 当前时间（ISO 8601 格式，含时区偏移）。
            limit: 返回的最大条数。

        Returns:
            [{"id": 1, "title": "...", "start_time": "...", "remind_before": 0}, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT id, title, start_time, remind_before
            FROM calendar_events
            WHERE user_id = ?
              AND datetime(start_time) >= datetime(?)
            ORDER BY datetime(start_time) ASC
            LIMIT ?
            """,
            (user_id, now_iso, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @classmethod
    async def get_due_events(cls) -> list[dict]:
        """取出所有到点待提醒的事件。

        核心算法（数据库即队列）：
            reminded = 0 且 (start_time - remind_before) <= 当前 UTC 时间

        Returns:
            [{"id": 1, "user_id": 123, "title": "...", "start_time": "..."}, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT id, user_id, title, start_time
            FROM calendar_events
            WHERE reminded = 0
              AND datetime(
                      start_time,
                      '-' || remind_before || ' minutes'
                  ) <= datetime('now')
            ORDER BY datetime(start_time) ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @classmethod
    async def mark_reminded(cls, event_id: int) -> None:
        """把事件标记为已提醒（出队，幂等）。

        Args:
            event_id: 事件 ID。
        """
        db = cls.get_db()
        await db.execute(
            """
            UPDATE calendar_events
            SET reminded = 1
            WHERE id = ?
            """,
            (event_id,),
        )
        await db.commit()

    @classmethod
    async def delete(cls, user_id: int, event_id: int) -> bool:
        """删除事件（仅限本人），返回是否成功。

        Args:
            user_id: Discord 用户 ID（防止删除他人事件）。
            event_id: 事件 ID。

        Returns:
            True 表示删除成功，False 表示未找到或无权限。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            DELETE FROM calendar_events
            WHERE id = ? AND user_id = ?
            """,
            (event_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    @classmethod
    async def get_by_id(cls, event_id: int) -> dict | None:
        """按 ID 读取事件。

        Args:
            event_id: 事件 ID。

        Returns:
            事件 dict，或 None（未找到）。
        """
        db = cls.get_db()
        cursor = await db.execute(
            """
            SELECT id, user_id, title, start_time, remind_before, reminded
            FROM calendar_events
            WHERE id = ?
            """,
            (event_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
