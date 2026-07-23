"""仓储基类：单例模式（适配 Database 单例连接）。

设计说明：
- 所有 Repository 为无状态单例，通过类属性 `_db` 共享数据库连接。
- 连接由组合根（main.py）在 Database.init() 后通过 init_all() 注入。
- 采用类方法（@classmethod）而非实例方法，避免到处传递 Repository 实例。
"""

import aiosqlite


class BaseRepository:
    """所有仓储的基类，持有共享数据库连接（单例）。"""

    _db: aiosqlite.Connection | None = None

    @classmethod
    def init(cls, db: aiosqlite.Connection) -> None:
        """注入数据库连接（由组合根在启动时调用一次）。

        Args:
            db: Database.connection 提供的全局共享连接。
        """
        cls._db = db

    @classmethod
    def get_db(cls) -> aiosqlite.Connection:
        """获取共享连接（fail-fast：未初始化时立即报错）。"""
        if cls._db is None:
            raise RuntimeError(
                "Repository 未初始化，请先调用 init_all(db_connection)"
            )
        return cls._db
