"""日历服务：日程事件的存储与到期查询。

所有事件一律入库（SQLite），由 core/scheduler 定时扫描到期事件并私信提醒。
"""

from core.database import get_connection


async def add_event(
    user_id: int,
    title: str,
    start_time: str,
    remind_before_minutes: int = 0,
) -> int:
    """创建日历事件。

    Args:
        user_id: Discord 用户 ID。
        title: 事件标题（如「开会」）。
        start_time: ISO 格式起始时间（含时区）。
        remind_before_minutes: 提前多少分钟提醒（0 表示到点提醒）。

    Returns:
        新事件的 rowid。
    """
    # TODO(实现): 写入 calendar_events 表
    raise NotImplementedError


async def list_upcoming(user_id: int, limit: int = 10) -> list[dict]:
    """列出用户未来的日程事件。"""
    # TODO(实现)
    raise NotImplementedError


async def pop_due_events(now_iso: str) -> list[dict]:
    """取出所有到点待提醒的事件（供调度器调用，取出后标记已提醒）。"""
    # TODO(实现)
    raise NotImplementedError
