"""Bangumi API 封装（中文动漫数据的唯一来源）。

提供：
- 动漫百科查询（中文标题、简介、角色）
- 季度新番列表（按星期几分组）
- 严格遵循 Bangumi API Header 要求

API 文档：https://bangumi.github.io/api/
"""

import logging
from typing import Any

import aiohttp

from core.config import Config

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
            return self._normalize_anime(anime)

        except Exception as exc:
            logger.error("Bangumi 查询失败: %s", exc)
            return None

    async def get_current_season_by_day(self) -> dict[int, list[dict]]:
        """获取当前季度新番，按星期几分组。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # Bangumi 每日放送（按星期几分类）
            result = await self._request("/calendar")

            if not result:
                logger.warning("Bangumi 季度查询无结果")
                return {}

            # 按星期几分组
            animes_by_day = {}
            for day_data in result:
                weekday = day_data.get("weekday", {}).get("id", 0) - 1  # Bangumi weekday id 从 1 开始
                if 0 <= weekday <= 6:
                    items = day_data.get("items", [])
                    # 按评分排序，取 top 10
                    sorted_items = sorted(
                        items,
                        key=lambda x: x.get("rating", {}).get("score", 0),
                        reverse=True,
                    )[:10]
                    animes_by_day[weekday] = [
                        self._normalize_anime(anime) for anime in sorted_items
                    ]

            logger.info("Bangumi 季度查询成功: %d 天有新番", len(animes_by_day))
            return animes_by_day

        except Exception as exc:
            logger.error("Bangumi 季度查询失败: %s", exc)
            return {}

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
        score_text = f"⭐ {score}/10" if score else "暂无评分"

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

        # 更新时间（如果有）
        air_time = anime.get("air_time", "未知时间")

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
            "air_time": air_time,  # 更新时间
        }
