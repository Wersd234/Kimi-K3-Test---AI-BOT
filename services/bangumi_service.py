"""Bangumi API 封装（中文动漫数据的唯一来源）。

提供：
- 动漫百科查询（中文标题、简介、角色）
- 季度新番列表
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

    async def get_current_season(self, page: int = 1) -> list[dict]:
        """获取当前季度热门新番列表。

        Args:
            page: 分页页码。

        Returns:
            新番信息 dict 列表。
        """
        try:
            from datetime import datetime

            now = datetime.now()
            year = now.year
            month = now.month

            # 计算当前季度
            if 1 <= month <= 3:
                season = "winter"
            elif 4 <= month <= 6:
                season = "spring"
            elif 7 <= month <= 9:
                season = "summer"
            else:
                season = "fall"

            # Bangumi 每日放送（按星期几分类）
            # 这里简化处理：直接获取热门动画
            result = await self._request(
                "/calendar",
            )

            if not result:
                logger.warning("Bangumi 季度查询无结果")
                return []

            # 提取所有番剧
            all_animes = []
            for day in result:
                if "items" in day:
                    all_animes.extend(day["items"])

            # 按评分排序，取前 20
            sorted_animes = sorted(
                all_animes,
                key=lambda x: x.get("rating", {}).get("score", 0),
                reverse=True,
            )[:20]

            logger.info("Bangumi 季度查询成功: %d 部新番", len(sorted_animes))

            # 转换为统一格式
            return [self._normalize_anime(anime) for anime in sorted_animes]

        except Exception as exc:
            logger.error("Bangumi 季度查询失败: %s", exc)
            return []

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
        }
