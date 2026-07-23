"""users 表仓储：用户档案（专属称呼、作息时间）。

所有方法为类方法（@classmethod），无需实例化即可调用。
"""

from repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """封装 users 表的全部 SQL 操作。"""

    @classmethod
    async def ensure_exists(cls, user_id: int) -> None:
        """确保用户记录存在（不存在则插入空档案）。

        用于满足子表外键约束（chat_history 等引用 users.user_id）。

        Args:
            user_id: Discord 用户 ID。
        """
        db = cls.get_db()
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,),
        )
        await db.commit()

    @classmethod
    async def upsert_honorific(cls, user_id: int, honorific: str) -> None:
        """插入或更新用户的专属称呼。

        Args:
            user_id: Discord 用户 ID。
            honorific: 专属称呼（如「主人」「大小姐」）。
        """
        db = cls.get_db()
        await db.execute(
            """
            INSERT INTO users (user_id, honorific)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET honorific = excluded.honorific
            """,
            (user_id, honorific),
        )
        await db.commit()

    @classmethod
    async def get_honorific(cls, user_id: int) -> str | None:
        """读取用户的专属称呼，未设置返回 None。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            称呼字符串，或 None。
        """
        db = cls.get_db()
        cursor = await db.execute(
            "SELECT honorific FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["honorific"] if row else None

    @classmethod
    async def upsert_bedtime(cls, user_id: int, bedtime: str) -> None:
        """插入或更新用户的作息时间（格式 "HH:MM"）。

        Args:
            user_id: Discord 用户 ID。
            bedtime: 作息时间字符串（如 "23:30"）。
        """
        db = cls.get_db()
        await db.execute(
            """
            INSERT INTO users (user_id, bedtime)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET bedtime = excluded.bedtime
            """,
            (user_id, bedtime),
        )
        await db.commit()

    @classmethod
    async def get_bedtime(cls, user_id: int) -> str | None:
        """读取用户的作息时间，未设置返回 None。

        Args:
            user_id: Discord 用户 ID。

        Returns:
            作息时间字符串（"HH:MM"），或 None。
        """
        db = cls.get_db()
        cursor = await db.execute(
            "SELECT bedtime FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["bedtime"] if row else None

    @classmethod
    async def get_all_with_bedtime(cls) -> list[dict]:
        """读取所有设置了作息时间的用户（供护肝提醒轮询）。

        Returns:
            [{"user_id": 123, "bedtime": "23:30"}, ...]
        """
        db = cls.get_db()
        cursor = await db.execute(
            "SELECT user_id, bedtime FROM users WHERE bedtime IS NOT NULL"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
