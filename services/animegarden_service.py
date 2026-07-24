"""Anime Garden API 封装（Yuc.wiki 番剧播出时间）。

提供：
- 番剧播出时间查询（Yuc.wiki 数据，时间准确）
- 与 Bangumi 结合使用（Bangumi 提供中文内容，Anime Garden 提供播出时间）

API 文档：https://github.com/yjl9903/AnimeGarden
"""

import logging
from typing import Any

import aiohttp

from core.config import Config

logger = logging.getLogger(__name__)


class AnimeGardenService:
    """Anime Garden API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置。
        """
        self._config = config
        self._api_url = "https://api.animegarden.com"
        self._headers = {
            "User-Agent": "KotoriBot/1.0 (https://github.com/Wersd234/Kimi-K3-Test---AI-BOT)",
            "Accept": "application/json",
        }
        logger.info("Anime Garden 客户端已初始化: %s", self._api_url)

    async def _request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """执行 HTTP 请求。

        Args:
            endpoint: API 端点。
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

    async def get_weekly_schedule(self) -> dict[int, list[dict]]:
        """获取本周播出时间表（从 Anime Garden 新番表）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # Anime Garden 新番表 API
            result = await self._request("/v1/schedule")

            if not result or "schedule" not in result:
                logger.warning("Anime Garden 新番表查询无结果")
                return {i: [] for i in range(7)}

            schedule = result["schedule"]

            # 按星期几分组
            animes_by_day: dict[int, list[dict]] = {i: [] for i in range(7)}

            for day_data in schedule:
                # 提取星期几（Anime Garden 使用 weekday 字段，0=周一，6=周日）
                weekday = day_data.get("weekday", -1)
                if weekday < 0 or weekday > 6:
                    continue

                items = day_data.get("items", [])

                for item in items:
                    # 提取标题
                    title = item.get("title", "Unknown")

                    # 提取播出时间（Anime Garden 使用 airTime 字段，格式如 "2026-07-25 15:30"）
                    air_time = item.get("airTime", "未知时间")

                    # 提取评分（如果有）
                    score = item.get("score", 0)

                    # 提取简介（如果有）
                    description = item.get("description", "暂无简介")

                    # 提取海报（如果有）
                    image_url = item.get("imageUrl", "")

                    # 构建动漫信息
                    anime_dict = {
                        "title": {
                            "romaji": title,
                            "english": title,
                            "native": title,  # Anime Garden 已经是中文
                        },
                        "coverImage": {"large": image_url},
                        "averageScore": score * 10 if score else None,  # 转换为 100 分制
                        "description": description,
                        "episodes": item.get("episodeCount", "?"),
                        "status": "连载中",
                        "air_time": air_time,
                        "characters": {"nodes": []},
                    }
                    animes_by_day[weekday].append(anime_dict)

            # 按播出时间排序
            for day in animes_by_day:
                animes_by_day[day].sort(key=lambda x: x.get("air_time", ""))

            logger.info("Anime Garden 周播出表获取成功: %d 天有新番", len(animes_by_day))
            return animes_by_day

        except Exception as exc:
            logger.error("Anime Garden 周播出表获取失败: %s", exc)
            return {i: [] for i in range(7)}

    async def get_anime_airing_time(self, title: str) -> str | None:
        """按标题搜索番剧，获取播出时间。

        Args:
            title: 番剧名称（中文）。

        Returns:
            播出时间字符串（如 "2026-07-25 15:30"），未找到返回 None。
        """
        try:
            # Anime Garden 搜索 API
            search_result = await self._request(
                "/v1/search",
                {"keyword": title}
            )

            if not search_result or "results" not in search_result:
                logger.warning("Anime Garden 搜索无结果: %s", title)
                return None

            results = search_result["results"]
            if not results:
                logger.warning("Anime Garden 搜索无结果: %s", title)
                return None

            # 取第一个结果
            anime = results[0]
            air_time = anime.get("airTime", "未知时间")

            logger.info("Anime Garden 播出时间查询成功: %s → %s", title, air_time)
            return air_time

        except Exception as exc:
            logger.error("Anime Garden 播出时间查询失败: %s", exc)
            return None
