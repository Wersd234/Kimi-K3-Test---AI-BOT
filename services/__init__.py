"""服务容器：集中管理所有 Service 实例（依赖注入）。"""

import logging

from core.config import Config
from services.ai_client import AIClient
from services.bangumi_service import BangumiService
from services.calendar_service import CalendarService
from services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)


class Services:
    """服务容器：集中管理所有 Service 实例（依赖注入）。"""

    def __init__(self, config: Config) -> None:
        """初始化所有 Service。

        Args:
            config: 全局配置。
        """
        self.ai_client = AIClient(config)
        self.bangumi_service = BangumiService(config)  # 使用 Bangumi
        self.calendar_service = CalendarService(config)
        self.watchlist_service = WatchlistService()
        logger.info("所有 Service 已初始化")
