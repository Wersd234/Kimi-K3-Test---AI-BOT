"""记忆服务：用户档案（称呼、作息）、短期上下文、长期偏好。

设计说明：
- 本层只表达业务规则（如格式校验、业务约束），不写 SQL。
- 所有数据库操作委托给 repositories/ 层。
- 当前阶段先实现用户档案部分（称呼、作息），
  短期上下文和长期偏好待 AI 对话功能落地时再补充。
"""

import re

from repositories import UserRepository

# 作息时间格式校验：HH:MM（00:00 - 23:59）
_BEDTIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class InvalidBedtimeError(ValueError):
    """作息时间格式非法时抛出的异常。"""


async def set_honorific(user_id: int, honorific: str) -> None:
    """设定用户的专属称呼。

    Args:
        user_id: Discord 用户 ID。
        honorific: 专属称呼（如「主人」「大小姐」）。
    """
    # 去除首尾空白，防止存储脏数据
    honorific = honorific.strip()
    if not honorific:
        raise ValueError("称呼不能为空")
    if len(honorific) > 20:
        raise ValueError("称呼过长（最多 20 个字符）")

    await UserRepository.upsert_honorific(user_id, honorific)


async def get_honorific(user_id: int) -> str | None:
    """读取用户的专属称呼。

    Args:
        user_id: Discord 用户 ID。

    Returns:
        称呼字符串，未设置返回 None。
    """
    return await UserRepository.get_honorific(user_id)


async def set_bedtime(user_id: int, bedtime: str) -> None:
    """设定用户的作息时间。

    Args:
        user_id: Discord 用户 ID。
        bedtime: 作息时间（格式 "HH:MM"，如 "23:30"）。

    Raises:
        InvalidBedtimeError: 时间格式非法时。
    """
    bedtime = bedtime.strip()
    if not _BEDTIME_PATTERN.match(bedtime):
        raise InvalidBedtimeError(
            f"时间格式应为 HH:MM（00:00-23:59），当前值: {bedtime!r}"
        )

    await UserRepository.upsert_bedtime(user_id, bedtime)


async def get_bedtime(user_id: int) -> str | None:
    """读取用户的作息时间。

    Args:
        user_id: Discord 用户 ID。

    Returns:
        作息时间字符串（"HH:MM"），未设置返回 None。
    """
    return await UserRepository.get_bedtime(user_id)


# TODO(AI 对话功能): 以下接口待后续实现
# - get_history(user_id) -> list[dict]  # 短期上下文
# - append_history(user_id, role, content) -> None
# - get_preferences(user_id) -> list[str]  # 长期偏好（RAG）
# - add_preference(user_id, preference) -> None
