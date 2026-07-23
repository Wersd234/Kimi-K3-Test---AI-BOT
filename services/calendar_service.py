"""日历服务：日程事件的存储与到期查询。

所有事件一律入库（SQLite），由 core/scheduler 定时扫描到期事件并私信提醒。
"""

import logging
from datetime import datetime, timezone

from core.config import Config
from repositories import CalendarRepository

logger = logging.getLogger(__name__)


class CalendarService:
    """日历业务逻辑（依赖注入 Config 和 CalendarRepository）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置（包含时区信息）。
        """
        self._config = config
        self._timezone = config.timezone
        logger.info("日历服务已初始化: 时区 %s", self._timezone)

    async def add_event(
        self,
        user_id: int,
        title: str,
        start_time: str,
        remind_before_minutes: int = 0,
    ) -> int:
        """创建日历事件。

        Args:
            user_id: Discord 用户 ID。
            title: 事件标题（如「开会」）。
            start_time: ISO 8601 格式起始时间（含时区偏移）。
            remind_before_minutes: 提前多少分钟提醒（0 表示到点提醒）。

        Returns:
            新事件的 rowid。
        """
        event_id = await CalendarRepository.add(
            user_id, title, start_time, remind_before_minutes
        )
        logger.info(
            "用户 %s 创建日历事件: %s (id: %d)",
            user_id,
            title,
            event_id,
        )
        return event_id

    async def list_upcoming(
        self, user_id: int, limit: int = 10
    ) -> list[dict]:
        """列出用户未来的日程事件。

        Args:
            user_id: Discord 用户 ID。
            limit: 返回的最大条数。

        Returns:
            事件列表（按时间升序）。
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        events = await CalendarRepository.list_upcoming(
            user_id, now_iso, limit
        )
        logger.info("用户 %s 查询日程: %d 个事件", user_id, len(events))
        return events

    async def get_due_events(self) -> list[dict]:
        """取出所有到点待提醒的事件（供调度器调用）。

        Returns:
            到点事件列表。
        """
        events = await CalendarRepository.get_due_events()
        if events:
            logger.info("发现 %d 个到点日历事件", len(events))
        return events

    async def mark_reminded(self, event_id: int) -> None:
        """把事件标记为已提醒。

        Args:
            event_id: 事件 ID。
        """
        await CalendarRepository.mark_reminded(event_id)
        logger.info("日历事件 %d 已标记为已提醒", event_id)

    async def delete_event(self, user_id: int, event_id: int) -> bool:
        """删除事件（仅限本人）。

        Args:
            user_id: Discord 用户 ID。
            event_id: 事件 ID。

        Returns:
            True 表示删除成功，False 表示未找到或无权限。
        """
        deleted = await CalendarRepository.delete(user_id, event_id)
        if deleted:
            logger.info("用户 %s 删除日历事件 %d", user_id, event_id)
        return deleted
