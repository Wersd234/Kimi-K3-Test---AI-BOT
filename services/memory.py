"""记忆服务：用户档案（称呼、作息）、短期上下文、长期偏好。

设计说明：
- 本层只表达业务规则（如格式校验、业务约束），不写 SQL。
- 所有数据库操作委托给 repositories/ 层。
"""

import re

from repositories import ChatRepository, PreferenceRepository, UserRepository

# 作息时间格式校验：HH:MM（00:00 - 23:59）
_BEDTIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# 短期上下文保留的最大轮数（1 轮 = user + assistant 2 条）
MAX_HISTORY_TURNS = 20


class InvalidBedtimeError(ValueError):
    """作息时间格式非法时抛出的异常。"""


async def set_honorific(user_id: int, honorific: str) -> None:
    """设定用户的专属称呼。"""
    honorific = honorific.strip()
    if not honorific:
        raise ValueError("称呼不能为空")
    if len(honorific) > 20:
        raise ValueError("称呼过长（最多 20 个字符）")

    await UserRepository.upsert_honorific(user_id, honorific)


async def get_honorific(user_id: int) -> str | None:
    """读取用户的专属称呼。"""
    return await UserRepository.get_honorific(user_id)


async def set_bedtime(user_id: int, bedtime: str) -> None:
    """设定用户的作息时间。"""
    bedtime = bedtime.strip()
    if not _BEDTIME_PATTERN.match(bedtime):
        raise InvalidBedtimeError(
            f"时间格式应为 HH:MM（00:00-23:59），当前值: {bedtime!r}"
        )

    await UserRepository.upsert_bedtime(user_id, bedtime)


async def get_bedtime(user_id: int) -> str | None:
    """读取用户的作息时间。"""
    return await UserRepository.get_bedtime(user_id)


async def get_history(user_id: int) -> list[dict]:
    """读取用户最近的对话上下文（OpenAI messages 格式，时间正序）。

    Args:
        user_id: Discord 用户 ID。

    Returns:
        [{"role": "user", "content": "..."}, ...]
    """
    return await ChatRepository.get_recent(
        user_id, limit=MAX_HISTORY_TURNS * 2
    )


async def append_history(user_id: int, role: str, content: str) -> None:
    """追加一条对话记录，并裁剪旧记录（滑窗策略）。

    Args:
        user_id: Discord 用户 ID。
        role: 角色（'user' / 'assistant' / 'system'）。
        content: 消息内容。
    """
    await UserRepository.ensure_exists(user_id)
    await ChatRepository.append(user_id, role, content)
    await ChatRepository.trim(user_id, keep=MAX_HISTORY_TURNS * 2)


async def get_preferences(user_id: int) -> list[str]:
    """读取用户全部长期偏好。

    Args:
        user_id: Discord 用户 ID。

    Returns:
        ["讨厌下雨", "喜欢机甲番", ...]
    """
    return await PreferenceRepository.list(user_id)


async def add_preference(user_id: int, preference: str) -> None:
    """写入一条长期偏好（自动去重）。

    Args:
        user_id: Discord 用户 ID。
        preference: 偏好内容（如「讨厌下雨」「喜欢机甲番」）。
    """
    if await PreferenceRepository.exists(user_id, preference):
        return
    await UserRepository.ensure_exists(user_id)
    await PreferenceRepository.add(user_id, preference)
