"""AniList GraphQL API 封装（播出时间表的唯一来源）。

设计说明：
- 使用 airingSchedule 端点一次性批量获取整周播出表，
  避免逐部查询导致的 404 和 429 限流问题。
- AniList 的 title.native 通常是日文，title.romaji 是罗马音；
  中文标题需结合 Bangumi 或用户自定义映射。
  但 AniList 的 title.userPreferred 可能返回英文，
  因此我们优先使用 native（日文）作为后备，
  并尽量从 Bangumi 获取中文名。
  然而 Bangumi /calendar 不提供播出时间，
  所以本服务负责提供时间，Bangumi 负责提供中文名。

  为了简化并避免限流，当前策略：
  - 播出时间：完全使用 AniList airingSchedule
  - 中文标题：尝试使用 Bangumi 搜索补全（可选，带缓存）
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.config import Config

logger = logging.getLogger(__name__)


class AniListService:
    """AniList API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置（包含 ANILIST_API_URL）。
        """
        self._config = config
        self._api_url = config.anilist_api_url
        logger.info("AniList 客户端已初始化: %s", self._api_url)

    async def _query(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """执行 GraphQL 查询。

        Args:
            query: GraphQL 查询语句。
            variables: 查询变量。

        Returns:
            查询结果 dict。

        Raises:
            aiohttp.ClientError: 网络请求失败。
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._api_url,
                json={"query": query, "variables": variables or {}},
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                result = await response.json()
                if "errors" in result:
                    logger.error("AniList GraphQL 错误: %s", result["errors"])
                    raise ValueError(f"GraphQL 错误: {result['errors']}")
                return result["data"]

    async def get_weekly_airing_schedule(self) -> dict[int, list[dict]]:
        """获取本周播出时间表，按星期几分组。

        一次请求获取整周数据，避免限流。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        # 计算本周一和下周日的时间范围
        now = datetime.now(timezone.utc)
        # 找到本周一（周一为一周的开始）
        monday = now - __import__("datetime").timedelta(days=now.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + __import__("datetime").timedelta(days=6, hours=23, minutes=59, seconds=59)

        # GraphQL 查询：airingSchedule
        query = """
        query ($start: Int, $end: Int) {
          Page(perPage: 500) {
            airingSchedules(airingAt_greater: $start, airingAt_lesser: $end, sort: TIME) {
              id
              airingAt
              episode
              media {
                id
                title {
                  romaji
                  english
                  native
                }
                coverImage {
                  large
                  medium
                }
                averageScore
                episodes
                status
                description
              }
            }
          }
        }
        """

        variables = {
            "start": int(monday.timestamp()),
            "end": int(sunday.timestamp()),
        }

        try:
            data = await self._query(query, variables)
            schedules = data.get("Page", {}).get("airingSchedules", [])
            logger.info("AniList 周播出表获取成功: %d 条记录", len(schedules))

            # 按星期几分组
            result: dict[int, list[dict]] = {i: [] for i in range(7)}
            for item in schedules:
                airing_at = item.get("airingAt")
                if not airing_at:
                    continue

                # 转换为本地时间
                dt = datetime.fromtimestamp(airing_at, tz=timezone.utc).astimezone()
                weekday = dt.weekday()  # 0=周一, 6=周日

                media = item.get("media", {})
                if not media:
                    continue

                # 去重：同一部番同一天可能出现多次（不同集数）
                media_id = media.get("id")
                if any(m.get("id") == media_id for m in result[weekday]):
                    continue

                # 提取标题
                title_obj = media.get("title", {})
                native_title = title_obj.get("native", "")
                romaji_title = title_obj.get("romaji", "")
                english_title = title_obj.get("english", "")

                # 评分
                score = media.get("averageScore")
                score_val = score if score else None

                # 简介
                description = media.get("description", "暂无简介")
                if description and len(description) > 200:
                    description = description[:200] + "..."

                # 集数与状态
                episodes = media.get("episodes", "?")
                status = media.get("status", "Unknown")
                status_map = {
                    "FINISHED": "已完结",
                    "RELEASING": "连载中",
                    "NOT_YET_RELEASED": "未播出",
                    "CANCELLED": "已取消",
                    "HIATUS": "暂停",
                }
                status_text = status_map.get(status, status)

                # 封面
                cover = media.get("coverImage", {})
                cover_url = cover.get("large") or cover.get("medium", "")

                # 格式化播出时间
                air_time_str = dt.strftime("%Y-%m-%d %H:%M")
                # 显示用简短格式（只保留时分）
                air_time_short = dt.strftime("%H:%M")

                anime_dict = {
                    "id": media_id,
                    "title": {
                        "romaji": romaji_title,
                        "english": english_title,
                        "native": native_title or romaji_title or english_title,
                    },
                    "coverImage": {"large": cover_url},
                    "averageScore": score_val,
                    "description": description,
                    "episodes": episodes,
                    "status": status_text,
                    "air_time": air_time_str,
                    "air_time_short": air_time_short,
                    "episode": item.get("episode", "?"),
                    "characters": {"nodes": []},  # AniList 此端点不含角色
                }
                result[weekday].append(anime_dict)

            # 按播出时间排序
            for day in result:
                result[day].sort(key=lambda x: x.get("air_time", ""))

            return result

        except Exception as exc:
            logger.error("AniList 周播出表获取失败: %s", exc)
            return {i: [] for i in range(7)}

    async def search_anime(self, title: str) -> dict | None:
        """按标题搜索动漫（用于 /anime 指令）。

        Args:
            title: 番剧名称（支持中文/日文/英文）。

        Returns:
            动漫信息 dict，未找到返回 None。
        """
        query = """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            id
            title {
              romaji
              english
              native
            }
            coverImage {
              large
            }
            averageScore
            episodes
            status
            description
            nextAiringEpisode {
              episode
              airingAt
            }
          }
        }
        """
        try:
            data = await self._query(query, {"search": title})
            media = data.get("Media")

            if not media:
                logger.warning("AniList 搜索无结果: %s", title)
                return None

            # 提取播出时间
            air_time = "未知时间"
            next_ep = media.get("nextAiringEpisode")
            if next_ep and next_ep.get("airingAt"):
                dt = datetime.fromtimestamp(next_ep["airingAt"], tz=timezone.utc).astimezone()
                air_time = dt.strftime("%Y-%m-%d %H:%M")

            # 提取标题
            title_obj = media.get("title", {})
            native_title = title_obj.get("native", "")
            romaji_title = title_obj.get("romaji", "")
            english_title = title_obj.get("english", "")

            # 评分
            score = media.get("averageScore")

            # 简介
            description = media.get("description", "暂无简介")
            if description and len(description) > 200:
                description = description[:200] + "..."

            # 集数与状态
            episodes = media.get("episodes", "?")
            status = media.get("status", "Unknown")
            status_map = {
                "FINISHED": "已完结",
                "RELEASING": "连载中",
                "NOT_YET_RELEASED": "未播出",
                "CANCELLED": "已取消",
                "HIATUS": "暂停",
            }
            status_text = status_map.get(status, status)

            # 封面
            cover = media.get("coverImage", {})
            cover_url = cover.get("large") or cover.get("medium", "")

            return {
                "title": {
                    "romaji": romaji_title,
                    "english": english_title,
                    "native": native_title or romaji_title or english_title,
                },
                "coverImage": {"large": cover_url},
                "averageScore": score,
                "description": description,
                "episodes": episodes,
                "status": status_text,
                "air_time": air_time,
                "characters": {"nodes": []},
            }

        except Exception as exc:
            logger.error("AniList 搜索失败: %s", exc)
            return None
