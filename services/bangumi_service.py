"""Bangumi API 封装（中文动漫数据的唯一来源）。

提供：
- 动漫百科查询（中文标题、简介、角色）
- 季度新番列表（按星期几分组，使用 AniList 播出时间）
- 严格遵循 Bangumi API Header 要求

API 文档：https://bangumi.github.io/api/
"""

import logging
from typing import Any

import aiohttp

from core.config import Config
from services.anilist_service import AniListService

logger = logging.getLogger(__name__)


class BangumiService:
    """Bangumi API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置。
        """
        self._config = config
        self._api_url = "https://api.bgm.tv"
        self._headers = {
            "User-Agent": "KotoriBot/1.0 (https://github.com/Wersd234/Kimi-K3-Test---AI-BOT)",
            "Accept": "application/json",
        }
        self._anilist = AniListService(config)  # 用于获取播出时间
        logger.info("Bangumi 客户端已初始化: %s", self._api_url)

    async def _request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """执行 HTTP 请求。

        Args:
            endpoint: API 端点（如 "/search/subject/..."）。
            params: 查询参数。

        Returns:
            响应 JSON dict。

        Raises:
            aiohttp.ClientError: 网络请求失败。
        """
        url = f"{self._api_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=self._headers, params=params or {}
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def search_anime(self, title: str) -> dict | None:
        """按标题搜索动漫，返回百科信息（中文）。

        Args:
            title: 番剧名称（支持中文/日文/英文）。

        Returns:
            动漫信息 dict，未找到返回 None。
        """
        try:
            # 搜索
            search_result = await self._request(
                "/search/subject/" + title,
                {"type": 2, "responseGroup": "large"},  # type=2 表示动画
            )

            if not search_result or "list" not in search_result:
                logger.warning("Bangumi 搜索无结果: %s", title)
                return None

            results = search_result["list"]
            if not results:
                logger.warning("Bangumi 搜索无结果: %s", title)
                return None

            # 取第一个结果
            anime = results[0]
            logger.info("Bangumi 查询成功: %s", anime.get("name_cn", anime.get("name")))

            # 转换为统一格式
            normalized = self._normalize_anime(anime)

            # 使用 AniList 获取实际播出时间（用日文标题）
            title_jp = anime.get("name", "")
            if title_jp:
                airing_time = await self._anilist.get_anime_airing_time(title_jp)
                if airing_time:
                    normalized["air_time"] = airing_time

            return normalized

        except Exception as exc:
            logger.error("Bangumi 查询失败: %s", exc)
            return None

    async def get_current_season_by_day(self) -> dict[int, list[dict]]:
        """获取当前季度新番，按星期几分组（使用 AniList 播出时间）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        # 直接使用 AniList 的播出时间表（避免 Bangumi 无时间数据）
        return await self._anilist.get_weekly_airing_schedule()

    def _normalize_anime(self, anime: dict) -> dict:
        """将 Bangumi 数据格式转换为统一格式（与 AniList 兼容）。

        Args:
            anime: Bangumi 返回的原始数据。

        Returns:
            统一格式的动漫信息 dict。
        """
        # 中文标题优先
        title_cn = anime.get("name_cn", "")
        title_jp = anime.get("name", "")

        # 简介
        summary = anime.get("summary", "暂无简介")

        # 评分
        rating = anime.get("rating", {})
        score = rating.get("score", 0)

        # 集数
        eps = anime.get("eps", "?")

        # 状态
        status = anime.get("status", "Unknown")
        status_map = {
            "airing": "连载中",
            "finished": "已完结",
            "not_yet_aired": "未播出",
        }
        status_text = status_map.get(status, status)

        # 海报
        images = anime.get("images", {})
        cover = images.get("large", "") or images.get("medium", "")

        # 角色（中文）
        characters = []
        if "crt" in anime:
            for char in anime["crt"][:5]:
                char_name = char.get("name_cn", char.get("name", ""))
                if char_name:
                    characters.append({"name": {"full": char_name}})

        # 播出日期（Bangumi 只有日期，没有时间）
        air_date = anime.get("air_date", "未知时间")

        return {
            "title": {
                "romaji": title_jp,
                "english": title_jp,
                "native": title_cn or title_jp,  # 中文优先
            },
            "coverImage": {"large": cover},
            "averageScore": score * 10 if score else None,  # 转换为 100 分制
            "description": summary,
            "episodes": eps,
            "status": status_text,
            "characters": {"nodes": characters},
            "air_time": air_date,  # 默认使用 air_date，后续可能被 AniList 覆盖
        }
