"""Bot 入口（组合根 Composition Root）。

职责：
- 加载并校验配置（fail-fast）
- 初始化数据库
- 初始化 Repository 层
- 初始化 Service 层
- 组装调度器并注册任务
- 启动 Discord 客户端，退出时释放全部资源

运行方式：
    python -m bot.main
"""

import asyncio
import logging

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.client import create_bot
from core.config import Config
from core.database import Database
from core.scheduler import ButlerScheduler
from repositories import init_all as init_repositories
from services import Services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def register_jobs(
    scheduler: ButlerScheduler, bot: "object", services: Services
) -> None:
    """向调度器注册全部周期任务（数据库即队列，重启可恢复）。

    机制层（core/scheduler）不感知业务，任务逻辑在此由组合根注入。

    TODO(实现): 注册真实的定时任务（早安简报、到点提醒、更新轮询、护肝提醒）。
    """
    # 每日早安简报：天气 + 今日日程 + 今日更新追番
    # scheduler.add_job(
    #     services.briefing_facade.send_morning_briefing,
    #     CronTrigger(hour=8, minute=0),
    #     job_id="morning_briefing",
    #     args=[bot],
    # )

    # 日历到点提醒：每分钟扫描一次数据库队列
    # scheduler.add_job(
    #     services.briefing_facade.send_due_event_reminders,
    #     IntervalTrigger(minutes=1),
    #     job_id="due_event_reminders",
    #     args=[bot],
    # )

    # 追番更新轮询：每 30 分钟检查 Bangumi 新集数
    # scheduler.add_job(
    #     services.briefing_facade.poll_anime_updates,
    #     IntervalTrigger(minutes=30),
    #     job_id="anime_update_poll",
    #     args=[bot],
    # )

    # 深夜护肝提醒：每小时整点检查是否该催睡
    # scheduler.add_job(
    #     services.briefing_facade.check_bedtime_reminder,
    #     CronTrigger(minute=0),
    #     job_id="bedtime_reminder",
    #     args=[bot],
    # )

    _ = (scheduler, bot, services, CronTrigger, IntervalTrigger)  # 暂未启用


async def main() -> None:
    """应用主流程：组装并启动所有基础设施。"""
    # 1. 加载配置并做启动校验（缺失凭证立即退出，给出清晰提示）
    config = Config.from_env()
    config.validate_required()

    # 2. 初始化数据库（单例连接 + 幂等建表）
    db = Database(config)
    await db.init()
    logger.info("数据库已就绪: %s", config.database_path)

    # 3. 初始化 Repository 层（注入共享数据库连接）
    init_repositories(db.connection)
    logger.info("Repository 层已初始化")

    # 4. 初始化 Service 层（依赖注入）
    services = Services(config)

    # 5. 组装调度器并注册任务
    bot = create_bot(config, services)
    scheduler = ButlerScheduler(config.timezone)
    register_jobs(scheduler, bot, services)
    scheduler.start()

    # 6. 启动 Discord 客户端；退出时按相反顺序释放资源
    try:
        await bot.start(config.discord_token)
    finally:
        scheduler.shutdown()
        await db.close()
        logger.info("资源已全部释放")


if __name__ == "__main__":
    asyncio.run(main())
