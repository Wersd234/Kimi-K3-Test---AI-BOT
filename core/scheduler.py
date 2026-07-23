"""定时调度机制层（Strategy 注册表 + 依赖反转）。

设计说明：
- 本模块是纯粹的「机制层」：只负责何时触发，不关心任务内容。
- 不 import services / bot（依赖反转）：任务逻辑由组合根（main.py）
  以可调用对象形式注册进来，彻底避免 core → services 的反向依赖
  与循环导入。
- 所有周期任务遵循「数据库即队列」：任务状态持久化在 SQLite，
  Bot 重启后重新扫描数据库即可恢复，不丢任何任务。
- 时区强一致：CronTrigger 缺省时区将跟随调度器的 timezone，
  统一使用配置中的 TZ。
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)

# 任务签名：async def job(bot) -> None
JobFunc = Callable[..., Awaitable[None]]


class ButlerScheduler:
    """调度器机制门面：注册、启动、关闭（不包含任何业务任务）。"""

    def __init__(self, timezone: str) -> None:
        """创建调度器，强制使用配置时区。

        Args:
            timezone: IANA 时区名（如 "Australia/Sydney"）。
        """
        self._scheduler = AsyncIOScheduler(timezone=timezone)
        # 自有状态位：底层 AsyncIOScheduler 的启动/关闭是延迟到事件循环
        # 执行的，其 running 属性在同步连续调用时不可靠，故自行跟踪。
        self._started = False

    def add_job(
        self,
        func: JobFunc,
        trigger: BaseTrigger,
        *,
        job_id: str,
        args: list[Any] | None = None,
    ) -> None:
        """注册一个周期任务（幂等，同 id 覆盖）。

        Args:
            func: 任务可调用对象（通常由组合根注入的 facade 方法）。
            trigger: APScheduler 触发器（CronTrigger / IntervalTrigger）。
            job_id: 任务唯一标识，用于日志与去重。
            args: 传给 func 的位置参数（如 [bot] 供任务发送 DM）。
        """
        self._scheduler.add_job(
            func,
            trigger,
            args=args or [],
            id=job_id,
            replace_existing=True,
        )
        logger.info("已注册定时任务: %s", job_id)

    def start(self) -> None:
        """启动调度器（幂等）。"""
        if not self._started:
            self._started = True
            self._scheduler.start()
            logger.info("调度器已启动")

    def shutdown(self) -> None:
        """优雅关闭调度器（幂等，不等待任务完成）。

        先翻转状态位再执行关闭，保证同步连续调用两次也是安全的。
        """
        if self._started:
            self._started = False
            self._scheduler.shutdown(wait=False)
            logger.info("调度器已关闭")
