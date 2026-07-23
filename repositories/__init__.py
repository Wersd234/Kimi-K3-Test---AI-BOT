"""数据访问层（Repository 模式）。

设计说明：
- 本层是整个项目中 SQL 语句的【唯一所在地】。
- services/ 层只表达业务规则，不直接写 SQL。
- 所有 Repository 为单例，共享 Database 提供的全局连接。
- 未来若从 SQLite 迁移到 PostgreSQL，仅需重写本层，
  上层业务代码零改动（Protected Variations）。
"""

from repositories.base import BaseRepository
from repositories.calendar_repository import CalendarRepository
from repositories.chat_repository import ChatRepository
from repositories.preference_repository import PreferenceRepository
from repositories.user_repository import UserRepository
from repositories.watchlist_repository import WatchlistRepository

__all__ = [
    "BaseRepository",
    "CalendarRepository",
    "ChatRepository",
    "PreferenceRepository",
    "UserRepository",
    "WatchlistRepository",
    "init_all",
]


def init_all(db_connection) -> None:
    """初始化所有 Repository（注入共享数据库连接）。

    由组合根（main.py）在 Database.init() 之后调用。

    Args:
        db_connection: Database.connection 提供的全局连接。
    """
    BaseRepository.init(db_connection)
