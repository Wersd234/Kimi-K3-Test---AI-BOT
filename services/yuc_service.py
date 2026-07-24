"""Yuc.wiki API 封装（中文番剧播出时间）。

提供：
- 番剧播出时间查询（中文网站，数据准确）
- 与 Bangumi 结合使用（Bangumi 提供中文内容，Yuc 提供播出时间）

网站：https://yuc.wiki/
"""

import logging
import re
from datetime import datetime
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from core.config import Config

logger = logging.getLogger(__name__)


class YucService:
    """Yuc.wiki API 客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置。

        Args:
            config: 全局配置。
        """
        self._config = config
        self._api_url = "https://yuc.wiki"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        logger.info("Yuc 客户端已初始化: %s", self._api_url)

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

    def _get_current_season_path(self) -> str:
        """获取当前季度的路径（如 /202607/）。

        Returns:
            季度路径字符串。
        """
        now = datetime.now()
        year = now.year
        month = now.month

        # 计算当前季度
        if 1 <= month <= 3:
            season = "01"  # 冬季
        elif 4 <= month <= 6:
            season = "04"  # 春季
        elif 7 <= month <= 9:
            season = "07"  # 夏季
        else:
            season = "10"  # 秋季

        return f"/{year}{season}/"

    def _parse_yuc_time(self, time_text: str) -> str:
        """解析 Yuc 时间格式，转换为具体播出时间。

        Yuc 时间格式示例：
        - 「7/5周日深夜」→ 下周日 24:30（即下周一 00:30）
        - 「7/9周四深夜」→ 下周四 24:30（即下周五 00:30）
        - 「7/6周日 20:30」→ 下周日 20:30

        Args:
            time_text: Yuc 原始时间字符串。

        Returns:
            格式化后的播出时间（如 "24:30" 或 "20:30"）。
        """
        if not time_text or time_text == "未知时间":
            return "未知时间"

        # 匹配「深夜」格式：7/5周日深夜 → 24:30
        # 匹配「具体时间」格式：7/6周日 20:30 → 20:30
        import re

        # 提取时间部分（如果有）
        time_match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        if time_match:
            # 已有具体时间（如 20:30）
            hour = int(time_match.group(1))
            minute = time_match.group(2)
            return f"{hour:02d}:{minute}"

        # 如果是「深夜」，默认 24:30
        if "深夜" in time_text:
            return "24:30"

        # 其他情况返回原始文本
        return time_text

    async def get_weekly_schedule(self) -> dict[int, list[dict]]:
        """获取本周播出时间表（从 Yuc 当前季度页面）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # 获取当前季度页面
            season_path = self._get_current_season_path()
            html = await self._request(season_path)
            soup = BeautifulSoup(html, "html.parser")

            # 查找每日放送表
            # Yuc 使用 <div><table class="date_"><tr><td class="date2">周一 (月)</td></tr></table></div>
            day_tables = soup.find_all("div", class_=lambda x: x and "date_" in x)

            result: dict[int, list[dict]] = {i: [] for i in range(7)}
            weekday_map = {
                "周一": 0, "周二": 1, "周三": 2, "周四": 3,
                "周五": 4, "周六": 5, "周日": 6,
            }

            for day_table in day_tables:
                # 提取星期几
                day_text = day_table.find("td", class_="date2")
                if not day_text:
                    continue

                day_name = day_text.text.strip()
                weekday = None
                for cn_day, wd in weekday_map.items():
                    if cn_day in day_name:
                        weekday = wd
                        break

                if weekday is None:
                    continue

                # 查找该天的番剧列表
                # Yuc 的番剧信息在 day_table 后面的兄弟元素中
                current = day_table.find_next_sibling()
                while current and not (current.name == "div" and current.get("class") and "date_" in current.get("class")):
                    if current.name == "table" and current.get("class") and "type_a_r" in current.get("class"):
                        # 提取番剧信息
                        title_elem = current.find("a")
                        title = title_elem.text.strip() if title_elem else "Unknown"

                        # 提取播出时间并转换为具体时间
                        time_elem = current.find("p", class_="broadcast_r")
                        time_text = time_elem.text.strip() if time_elem else "未知时间"
                        air_time = self._parse_yuc_time(time_text)

                        # 构建动漫信息
                        anime = {
                            "title": {
                                "romaji": title,
                                "english": title,
                                "native": title,  # Yuc 已经是中文
                            },
                            "coverImage": {"large": ""},
                            "averageScore": None,
                            "description": "暂无简介",
                            "episodes": "?",
                            "status": "连载中",
                            "air_time": air_time,
                            "characters": {"nodes": []},
                        }
                        result[weekday].append(anime)

                    current = current.find_next_sibling()

            logger.info("Yuc 周播出表获取成功: %d 天有新番", len(result))
            return result

        except Exception as exc:
            logger.error("Yuc 周播出表获取失败: %s", exc)
            return {i: [] for i in range(7)}

    async def get_anime_airing_time(self, title: str) -> str | None:
        """按标题搜索番剧，获取播出时间。

        Args:
            title: 番剧名称（中文）。

        Returns:
            播出时间字符串（如 "2026-07-25 15:30"），未找到返回 None。
        """
        try:
            # 获取当前季度页面
            season_path = self._get_current_season_path()
            html = await self._request(season_path)
            soup = BeautifulSoup(html, "html.parser")

            # 在所有番剧中搜索匹配的标题
            all_animes = soup.find_all("table", class_=lambda x: x and "type_a_r" in x)

            for anime_table in all_animes:
                title_elem = anime_table.find("a")
                if not title_elem:
                    continue

                anime_title = title_elem.text.strip()
                # 模糊匹配
                if title in anime_title or anime_title in title:
                    time_elem = anime_table.find("p", class_="broadcast_r")
                    if time_elem:
                        time_text = time_elem.text.strip()
                        air_time = self._parse_yuc_time(time_text)
                        logger.info("Yuc 播出时间查询成功: %s → %s", title, air_time)
                        return air_time

            logger.warning("Yuc 未找到番剧: %s", title)
            return None

        except Exception as exc:
            logger.error("Yuc 播出时间查询失败: %s", exc)
            return None
