"""Mikan Project API 封装（中文番剧播出时间）。

提供：
- 番剧播出时间查询（中文网站，数据准确）
- 与 Bangumi 结合使用（Bangumi 提供中文内容，Mikan 提供播出时间）

API 文档：https://mikanani.me/Home/Help
"""

import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from core.config import Config

logger = logging.getLogger(__name__)


class MikanService:
    """Mikan Project API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置。
        """
        self._config = config
        self._api_url = "https://mikanani.me"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        logger.info("Mikan 客户端已初始化: %s", self._api_url)

    async def _request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> str:
        """执行 HTTP 请求。

        Args:
            endpoint: API 端点。
            params: 查询参数。

        Returns:
            响应 HTML 文本。

        Raises:
            aiohttp.ClientError: 网络请求失败。
        """
        url = f"{self._api_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=self._headers, params=params or {}
            ) as response:
                response.raise_for_status()
                return await response.text()

    async def get_anime_airing_time(self, title: str) -> str | None:
        """按标题搜索番剧，获取播出时间。

        Args:
            title: 番剧名称（中文）。

        Returns:
            播出时间字符串（如 "2026-07-25 15:30"），未找到返回 None。
        """
        try:
            # Mikan 搜索页面
            html = await self._request("/Home/Search", {"searchstr": title})
            soup = BeautifulSoup(html, "html.parser")

            # 查找第一个搜索结果
            result = soup.find("div", class_="search-result-item")
            if not result:
                logger.warning("Mikan 搜索无结果: %s", title)
                return None

            # 提取播出时间（如果有）
            time_elem = result.find("span", class_="air-time")
            if time_elem:
                air_time = time_elem.text.strip()
                logger.info("Mikan 播出时间查询成功: %s → %s", title, air_time)
                return air_time

            # 如果没有找到时间，返回 None
            logger.info("Mikan 未找到播出时间: %s", title)
            return None

        except Exception as exc:
            logger.error("Mikan 播出时间查询失败: %s", exc)
            return None

    async def get_weekly_schedule(self) -> dict[int, list[dict]]:
        """获取本周播出时间表（从 Mikan 首页）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # Mikan 首页有每日放送表
            html = await self._request("/")
            soup = BeautifulSoup(html, "html.parser")

            # 查找每日放送表
            schedule_table = soup.find("table", class_="schedule-table")
            if not schedule_table:
                logger.warning("Mikan 未找到每日放送表")
                return {i: [] for i in range(7)}

            # 解析表格
            result: dict[int, list[dict]] = {i: [] for i in range(7)}
            rows = schedule_table.find_all("tr")

            for row in rows[1:]:  # 跳过表头
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                # 提取数据
                title_elem = cols[0].find("a")
                title = title_elem.text.strip() if title_elem else "Unknown"
                time_text = cols[1].text.strip()
                weekday_text = cols[2].text.strip()

                # 解析星期几
                weekday_map = {
                    "周一": 0, "周二": 1, "周三": 2, "周四": 3,
                    "周五": 4, "周六": 5, "周日": 6,
                }
                weekday = weekday_map.get(weekday_text, -1)
                if weekday == -1:
                    continue

                # 构建动漫信息
                anime = {
                    "title": {
                        "romaji": title,
                        "english": title,
                        "native": title,  # Mikan 已经是中文
                    },
                    "coverImage": {"large": ""},
                    "averageScore": None,
                    "description": "暂无简介",
                    "episodes": "?",
                    "status": "连载中",
                    "air_time": time_text,
                    "characters": {"nodes": []},
                }
                result[weekday].append(anime)

            logger.info("Mikan 周播出表获取成功: %d 天有新番", len(result))
            return result

        except Exception as exc:
            logger.error("Mikan 周播出表获取失败: %s", exc)
            return {i: [] for i in range(7)}
