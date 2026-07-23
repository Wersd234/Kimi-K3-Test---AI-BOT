"""SQLite 数据库层（Singleton 连接 + 建表 Schema）。

设计说明：
- 单例连接（Singleton）：SQLite 是单写者数据库，单连接 +
  aiosqlite 内部队列串行化是最安全的并发模型，避免连接泄漏。
- WAL 模式：读写不互斥，「读记忆」与「写日历」可并行。
- 外键约束：删除用户时级联清理其全部数据（记忆/追番/日程）。
- 建表幂等：全部 CREATE TABLE IF NOT EXISTS，每次启动执行无副作用。
- 数据落盘：数据库文件位于容器 /app/bot_data，经 Docker Volume
  映射到宿主机 ./data，Bot 升级重启数据不丢失。
"""

import os

import aiosqlite

from core.config import Config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    honorific  TEXT,                     -- 专属称呼，如「主人」「大小姐」
    bedtime    TEXT,                     -- 作息时间 "HH:MM"，护肝提醒用
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL
               REFERENCES users(user_id) ON DELETE CASCADE,
    role       TEXT NOT NULL
               CHECK (role IN ('user', 'assistant', 'system')),
    content    TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_history_user
    ON chat_history (user_id, id);

CREATE TABLE IF NOT EXISTS preferences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL
               REFERENCES users(user_id) ON DELETE CASCADE,
    content    TEXT NOT NULL,            -- 如「讨厌下雨」「喜欢机甲番」
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_preferences_user
    ON preferences (user_id);

CREATE TABLE IF NOT EXISTS watchlist (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL
                          REFERENCES users(user_id) ON DELETE CASCADE,
    anime_id              INTEGER NOT NULL,   -- AniList 媒体 ID
    anime_title           TEXT NOT NULL,      -- 冗余存储，减少 API 调用
    last_notified_episode INTEGER,            -- 上次已提醒的集数
    added_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, anime_id)                -- 防止重复追番
);
CREATE INDEX IF NOT EXISTS idx_watchlist_user
    ON watchlist (user_id);

CREATE TABLE IF NOT EXISTS calendar_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL
                  REFERENCES users(user_id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    start_time    TEXT NOT NULL,              -- ISO 8601（含时区偏移）
    remind_before INTEGER NOT NULL DEFAULT 0, -- 提前多少分钟提醒
    reminded      INTEGER NOT NULL DEFAULT 0, -- 0=待提醒 1=已提醒
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_calendar_events_due
    ON calendar_events (reminded, start_time);
"""


class Database:
    """数据库单例门面：持有全局唯一连接，负责初始化与释放。

    使用方式（组合根）：
        db = Database(config)
        await db.init()
        ...
        await db.close()
    """

    def __init__(self, config: Config) -> None:
        """注入配置（显式依赖，而非读取全局状态）。"""
        self._path = config.database_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """打开连接、设置 PRAGMA、建表（幂等）。"""
        db_dir = os.path.dirname(self._path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row

        # WAL：读写并行；外键：级联删除
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    @property
    def connection(self) -> aiosqlite.Connection:
        """全局共享连接（Repository 层经此访问，fail-fast）。"""
        if self._conn is None:
            raise RuntimeError("数据库未初始化，请先调用 Database.init()")
        return self._conn

    async def close(self) -> None:
        """优雅关闭连接（幂等，可重复调用）。"""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
