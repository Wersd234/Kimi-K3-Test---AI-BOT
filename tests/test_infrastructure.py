"""基础设施层单元测试。

测试范围：
- core/config.py: 配置加载
- core/database.py: 连接管理与建表
- repositories/: 所有 SQL 操作

运行方式：
    python -m pytest tests/test_infrastructure.py -v
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

# 在导入配置前设置测试环境
os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["TZ"] = "Australia/Sydney"

from core.config import config
from core.database import close_database, get_connection, init_database
from repositories import (
    CalendarRepository,
    ChatRepository,
    PreferenceRepository,
    UserRepository,
    WatchlistRepository,
)


@pytest_asyncio.fixture
async def db():
    """数据库连接 fixture。"""
    await init_database()
    yield await get_connection()
    await close_database()
    # 清理测试数据库文件
    if os.path.exists(config.database_path):
        os.unlink(config.database_path)


@pytest.fixture
def user_repo(db):
    """用户仓储 fixture。"""
    return UserRepository(db)


@pytest.fixture
def chat_repo(db):
    """对话仓储 fixture。"""
    return ChatRepository(db)


@pytest.fixture
def pref_repo(db):
    """偏好仓储 fixture。"""
    return PreferenceRepository(db)


@pytest.fixture
def watch_repo(db):
    """追番仓储 fixture。"""
    return WatchlistRepository(db)


@pytest.fixture
def cal_repo(db):
    """日历仓储 fixture。"""
    return CalendarRepository(db)


class TestConfig:
    """配置测试。"""

    def test_config_is_frozen(self):
        """配置对象不可变。"""
        with pytest.raises(Exception):
            config.discord_token = "hacked"

    def test_config_has_defaults(self):
        """配置有合理默认值。"""
        assert config.timezone == "Australia/Sydney"
        assert config.ai_base_url.startswith("http")
        assert config.morning_briefing_hour == 8


class TestDatabase:
    """数据库测试。"""

    @pytest.mark.asyncio
    async def test_connection_singleton(self, db):
        """连接是单例。"""
        conn1 = await get_connection()
        conn2 = await get_connection()
        assert conn1 is conn2

    @pytest.mark.asyncio
    async def test_tables_exist(self, db):
        """所有表已创建。"""
        cursor = await db.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        tables = [row["name"] for row in await cursor.fetchall()]
        assert "users" in tables
        assert "chat_history" in tables
        assert "preferences" in tables
        assert "watchlist" in tables
        assert "calendar_events" in tables

    @pytest.mark.asyncio
    async def test_wal_mode(self, db):
        """WAL 模式已开启。"""
        cursor = await db.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0].upper() == "WAL"

    @pytest.mark.asyncio
    async def test_foreign_keys(self, db):
        """外键约束已开启。"""
        cursor = await db.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1


class TestUserRepository:
    """用户仓储测试。"""

    @pytest.mark.asyncio
    async def test_upsert_honorific(self, user_repo):
        """设定专属称呼。"""
        user_id = 123456789

        # 首次插入
        await user_repo.upsert_honorific(user_id, "主人")
        result = await user_repo.get_honorific(user_id)
        assert result == "主人"

        # 更新
        await user_repo.upsert_honorific(user_id, "大小姐")
        result = await user_repo.get_honorific(user_id)
        assert result == "大小姐"

    @pytest.mark.asyncio
    async def test_get_honorific_not_exists(self, user_repo):
        """读取不存在的称呼返回 None。"""
        result = await user_repo.get_honorific(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_bedtime(self, user_repo):
        """设定作息时间。"""
        user_id = 123456789
        await user_repo.upsert_bedtime(user_id, "23:30")
        result = await user_repo.get_bedtime(user_id)
        assert result == "23:30"

    @pytest.mark.asyncio
    async def test_get_all_with_bedtime(self, user_repo):
        """读取所有设置了作息的用户。"""
        await user_repo.upsert_bedtime(111, "23:00")
        await user_repo.upsert_bedtime(222, "00:30")
        await user_repo.upsert_honorific(333, "无作息用户")

        users = await user_repo.get_all_with_bedtime()
        assert len(users) == 2
        user_ids = [u["user_id"] for u in users]
        assert 111 in user_ids
        assert 222 in user_ids
        assert 333 not in user_ids


class TestChatRepository:
    """对话仓储测试。"""

    @pytest.mark.asyncio
    async def test_append_and_get(self, chat_repo, user_repo):
        """追加和读取对话。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        await chat_repo.append(user_id, "user", "你好")
        await chat_repo.append(user_id, "assistant", "你好，主人！")

        history = await chat_repo.get_recent(user_id, limit=10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "你好"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_recent_order(self, chat_repo, user_repo):
        """最近对话按时间正序返回。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        # 插入 5 条消息
        for i in range(5):
            await chat_repo.append(user_id, "user", f"消息{i}")

        # 只取最近 3 条
        history = await chat_repo.get_recent(user_id, limit=3)
        assert len(history) == 3
        # 应该是消息2、消息3、消息4（正序）
        assert history[0]["content"] == "消息2"
        assert history[1]["content"] == "消息3"
        assert history[2]["content"] == "消息4"

    @pytest.mark.asyncio
    async def test_trim_to_limit(self, chat_repo, user_repo):
        """裁剪历史记录。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        # 插入 10 条
        for i in range(10):
            await chat_repo.append(user_id, "user", f"消息{i}")

        # 裁剪到只保留 5 条
        await chat_repo.trim_to_limit(user_id, limit=5)

        history = await chat_repo.get_recent(user_id, limit=100)
        assert len(history) == 5
        # 应该保留最新的 5 条
        assert history[0]["content"] == "消息5"
        assert history[-1]["content"] == "消息9"


class TestPreferenceRepository:
    """偏好仓储测试。"""

    @pytest.mark.asyncio
    async def test_add_and_list(self, pref_repo, user_repo):
        """添加和读取偏好。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        await pref_repo.add(user_id, "讨厌下雨")
        await pref_repo.add(user_id, "喜欢机甲番")

        prefs = await pref_repo.list_all(user_id)
        assert len(prefs) == 2
        assert "讨厌下雨" in prefs
        assert "喜欢机甲番" in prefs

    @pytest.mark.asyncio
    async def test_delete(self, pref_repo, user_repo):
        """删除偏好。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        await pref_repo.add(user_id, "讨厌下雨")
        deleted = await pref_repo.delete(user_id, "讨厌下雨")
        assert deleted == 1

        prefs = await pref_repo.list_all(user_id)
        assert "讨厌下雨" not in prefs


class TestWatchlistRepository:
    """追番仓储测试。"""

    @pytest.mark.asyncio
    async def test_add_new(self, watch_repo, user_repo):
        """添加新追番。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        is_new = await watch_repo.add(user_id, 12345, "进击的巨人")
        assert is_new is True

    @pytest.mark.asyncio
    async def test_add_duplicate(self, watch_repo, user_repo):
        """重复添加返回 False。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        await watch_repo.add(user_id, 12345, "进击的巨人")
        is_new = await watch_repo.add(user_id, 12345, "进击的巨人")
        assert is_new is False

    @pytest.mark.asyncio
    async def test_list_by_user(self, watch_repo, user_repo):
        """读取用户追番列表。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        await watch_repo.add(user_id, 111, "番剧A")
        await watch_repo.add(user_id, 222, "番剧B")

        watchlist = await watch_repo.list_by_user(user_id)
        assert len(watchlist) == 2
        titles = [w["anime_title"] for w in watchlist]
        assert "番剧A" in titles
        assert "番剧B" in titles

    @pytest.mark.asyncio
    async def test_list_distinct_anime(self, watch_repo, user_repo):
        """读取所有被追踪的番剧 ID。"""
        await user_repo.upsert_honorific(111, "用户1")
        await user_repo.upsert_honorific(222, "用户2")

        await watch_repo.add(111, 12345, "番剧A")
        await watch_repo.add(222, 12345, "番剧A")  # 重复
        await watch_repo.add(222, 67890, "番剧B")

        anime_ids = await watch_repo.list_distinct_anime()
        assert len(anime_ids) == 2
        assert 12345 in anime_ids
        assert 67890 in anime_ids


class TestCalendarRepository:
    """日历仓储测试。"""

    @pytest.mark.asyncio
    async def test_add_event(self, cal_repo, user_repo):
        """添加日历事件。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        tz = ZoneInfo("Australia/Sydney")
        start_time = datetime.now(tz) + timedelta(hours=1)

        event_id = await cal_repo.add(
            user_id=user_id,
            title="开会",
            start_time=start_time.isoformat(),
            remind_before_minutes=15,
        )
        assert event_id > 0

    @pytest.mark.asyncio
    async def test_list_upcoming(self, cal_repo, user_repo):
        """读取未来事件。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        tz = ZoneInfo("Australia/Sydney")
        now = datetime.now(tz)

        # 添加一个未来事件
        future = now + timedelta(hours=2)
        await cal_repo.add(
            user_id, "未来事件", future.isoformat(), 0
        )

        # 添加一个过去事件
        past = now - timedelta(hours=1)
        await cal_repo.add(
            user_id, "过去事件", past.isoformat(), 0
        )

        events = await cal_repo.list_upcoming(user_id, limit=10)
        assert len(events) == 1
        assert events[0]["title"] == "未来事件"

    @pytest.mark.asyncio
    async def test_get_due_events(self, cal_repo, user_repo):
        """获取到点事件（数据库即队列）。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        tz = ZoneInfo("Australia/Sydney")
        now = datetime.now(tz)

        # 创建一个 5 分钟后到期的事件
        start_time = now + timedelta(minutes=5)
        await cal_repo.add(
            user_id, "即将到期", start_time.isoformat(), 0
        )

        # 创建一个 1 小时后到期的事件
        start_time = now + timedelta(hours=1)
        await cal_repo.add(
            user_id, "还未到期", start_time.isoformat(), 0
        )

        # 6 分钟后检查
        check_time = (now + timedelta(minutes=6)).isoformat()
        due_events = await cal_repo.get_due_events(check_time)

        assert len(due_events) == 1
        assert due_events[0]["title"] == "即将到期"

    @pytest.mark.asyncio
    async def test_mark_reminded(self, cal_repo, user_repo):
        """标记已提醒。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        tz = ZoneInfo("Australia/Sydney")
        start_time = datetime.now(tz) + timedelta(minutes=1)
        event_id = await cal_repo.add(
            user_id, "测试事件", start_time.isoformat(), 0
        )

        # 标记为已提醒
        await cal_repo.mark_reminded(event_id)

        # 再次查询到点事件，应该为空
        check_time = (datetime.now(tz) + timedelta(minutes=2)).isoformat()
        due_events = await cal_repo.get_due_events(check_time)
        assert len(due_events) == 0

    @pytest.mark.asyncio
    async def test_delete_event(self, cal_repo, user_repo):
        """删除事件。"""
        user_id = 123456789
        await user_repo.upsert_honorific(user_id, "测试")

        tz = ZoneInfo("Australia/Sydney")
        start_time = datetime.now(tz) + timedelta(hours=1)
        event_id = await cal_repo.add(
            user_id, "要删除的事件", start_time.isoformat(), 0
        )

        # 删除成功
        deleted = await cal_repo.delete(user_id, event_id)
        assert deleted is True

        # 再次删除返回 False
        deleted = await cal_repo.delete(user_id, event_id)
        assert deleted is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
