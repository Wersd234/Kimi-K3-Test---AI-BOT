"""弹弹play API 封装（番剧播出时间）。

提供：
- 番剧播出时间查询（中文网站，数据准确）
- 与 Bangumi 结合使用（Bangumi 提供中文内容，弹弹play 提供播出时间）

API 文档：https://api.dandanplay.net/swagger/ui/index.html
"""

import logging
from typing import Any

import aiohttp

from core.config import Config

logger = logging.getLogger(__name__)


class DandanplayService:
    """弹弹play API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置。
        """
        self._config = config
        self._api_url = "https://api.dandanplay.net/api/v2"
        # 弹弹play API 需要更严格的 User-Agent 和 Accept
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.dandanplay.com/",
        }
        logger.info("弹弹play 客户端已初始化: %s", self._api_url)

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
        """获取本周播出时间表（从弹弹play 新番表）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # 弹弹play 新番表 API
            result = await self._request("/bangumi/shinbangumi")

            if not result or "bangumiList" not in result:
                logger.warning("弹弹play 新番表查询无结果")
                return {i: [] for i in range(7)}

            bangumi_list = result["bangumiList"]

            # 按星期几分组
            animes_by_day: dict[int, list[dict]] = {i: [] for i in range(7)}

            for anime in bangumi_list:
                # 提取星期几（弹弹play 使用 airDayOfWeek 字段，1=周一，7=周日）
                air_day = anime.get("airDayOfWeek", 0)
                if air_day < 1 or air_day > 7:
                    continue

                weekday = air_day - 1  # 转换为 0=周一, 6=周日

                # 提取标题
                title = anime.get("animeTitle", "Unknown")

                # 提取播出时间（弹弹play 使用 airTime 字段，格式如 "2026-07-25 15:30"）
                air_time = anime.get("airTime", "未知时间")

                # 提取评分（如果有）
                rating = anime.get("rating", {})
                score = rating.get("score", 0) if rating else 0

                # 提取简介（如果有）
                description = anime.get("description", "暂无简介")

                # 提取海报（如果有）
                image_url = anime.get("imageUrl", "")

                # 构建动漫信息
                anime_dict = {
                    "title": {
                        "romaji": title,
                        "english": title,
                        "native": title,  # 弹弹play 已经是中文
                    },
                    "coverImage": {"large": image_url},
                    "averageScore": score * 10 if score else None,  # 转换为 100 分制
                    "description": description,
                    "episodes": anime.get("episodeCount", "?"),
                    "status": "连载中",
                    "air_time": air_time,
                    "characters": {"nodes": []},
                }
                animes_by_day[weekday].append(anime_dict)

            # 按播出时间排序
            for day in animes_by_day:
                animes_by_day[day].sort(key=lambda x: x.get("air_time", ""))

            logger.info("弹弹play 周播出表获取成功: %d 天有新番", len(animes_by_day))
            return animes_by_day

        except Exception as exc:
            logger.error("弹弹play 周播出表获取失败: %s", exc)
            return {i: [] for i in range(7)}

    async def get_anime_airing_time(self, title: str) -> str | None:
        """按标题搜索番剧，获取播出时间。

        Args:
            title: 番剧名称（中文）。

        Returns:
            播出时间字符串（如 "2026-07-25 15:30"），未找到返回 None。
        """
        try:
            # 弹弹play 搜索 API
            search_result = await self._request(
                "/search/anime",
                {"keyword": title}
            )

            if not search_result or "animes" not in search_result:
                logger.warning("弹弹play 搜索无结果: %s", title)
                return None

            animes = search_result["animes"]
            if not animes:
                logger.warning("弹弹play 搜索无结果: %s", title)
                return None

            # 取第一个结果
            anime = animes[0]
            air_time = anime.get("airTime", "未知时间")

            logger.info("弹弹play 播出时间查询成功: %s → %s", title, air_time)
            return air_time

        except Exception as exc:
            logger.error("弹弹play 播出时间查询失败: %s", exc)
            return None
