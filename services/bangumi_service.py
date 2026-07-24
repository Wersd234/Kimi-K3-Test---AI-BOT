"""Bangumi API 封装（中文动漫内容的唯一来源）。

设计说明：
- Bangumi 提供中文标题、中文简介、中文角色。
- Anime Garden 提供精确播出时间（Yuc.wiki 数据，时间准确）。
- 两者结合：Bangumi 负责内容，Anime Garden 负责时间。

API 文档：https://bangumi.github.io/api/
"""

import logging
from typing import Any

import aiohttp

from core.config import Config
from services.animegarden_service import AnimeGardenService

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
        self._animegarden = AnimeGardenService(config)  # 用于获取播出时间
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

            # 使用 Anime Garden 获取实际播出时间（用中文标题）
            title_cn = anime.get("name_cn", anime.get("name", ""))
            if title_cn:
                airing_time = await self._animegarden.get_anime_airing_time(title_cn)
                if airing_time:
                    normalized["air_time"] = airing_time

            return normalized

        except Exception as exc:
            logger.error("Bangumi 查询失败: %s", exc)
            return None

    async def get_current_season_by_day(self) -> dict[int, list[dict]]:
        """获取当前季度新番，按星期几分组（Bangumi 内容 + Anime Garden 时间）。

        Returns:
            按星期几分组的新番 dict {0: [...], 1: [...], ..., 6: [...]}
            0=周一, 6=周日
        """
        try:
            # 1. 先获取 Anime Garden 的整周播出时间表（Yuc.wiki 数据，时间准确）
            animegarden_schedule = await self._animegarden.get_weekly_schedule()

            # 2. 获取 Bangumi 的每日放送（中文内容）
            bangumi_result = await self._request("/calendar")

            if not bangumi_result:
                logger.warning("Bangumi 季度查询无结果，使用纯 Anime Garden 数据")
                return animegarden_schedule

            # 3. 合并：Bangumi 内容 + Anime Garden 时间
            animes_by_day = {}
            for day_data in bangumi_result:
                weekday = day_data.get("weekday", {}).get("id", 0) - 1  # Bangumi weekday id 从 1 开始
                if 0 <= weekday <= 6:
                    items = day_data.get("items", [])
                    # 按评分排序，取 top 10
                    sorted_items = sorted(
                        items,
                        key=lambda x: x.get("rating", {}).get("score", 0),
                        reverse=True,
                    )[:10]

                    animes_by_day[weekday] = []
                    for anime in sorted_items:
                        normalized = self._normalize_anime(anime)

                        # 尝试从 Anime Garden 匹配播出时间（用中文标题匹配）
                        title_cn = anime.get("name_cn", anime.get("name", "")).strip()
                        if title_cn and weekday in animegarden_schedule:
                            matched_time = self._fuzzy_match_animegarden_time(
                                title_cn, animegarden_schedule[weekday]
                            )
                            if matched_time:
                                normalized["air_time"] = matched_time
                            else:
                                # 如果 Anime Garden 没有匹配到，显示「未知时间」而不是 Bangumi 的日期
                                normalized["air_time"] = "未知时间"

                        animes_by_day[weekday].append(normalized)

            logger.info("Bangumi + Anime Garden 季度查询成功: %d 天有新番", len(animes_by_day))
            return animes_by_day

        except Exception as exc:
            logger.error("Bangumi 季度查询失败: %s", exc)
            # 失败时回退到纯 Anime Garden 数据
            return await self._animegarden.get_weekly_schedule()

    def _fuzzy_match_animegarden_time(
        self, title_cn: str, animegarden_animes: list[dict]
    ) -> str | None:
        """模糊匹配 Anime Garden 播出时间。

        匹配策略（按优先级）：
        1. 完全匹配（忽略大小写和空格）
        2. 包含匹配（一个标题包含另一个）

        Args:
            title_cn: Bangumi 中文标题。
            animegarden_animes: Anime Garden 同一天的番剧列表。

        Returns:
            匹配到的播出时间，未匹配返回 None。
        """
        if not title_cn:
            return None

        # 标准化函数：小写、去空格、去特殊字符
        def normalize(s: str) -> str:
            return "".join(c.lower() for c in s if c.isalnum())

        title_norm = normalize(title_cn)

        for animegarden_anime in animegarden_animes:
            animegarden_title = animegarden_anime.get("title", {})
            animegarden_native = animegarden_title.get("native", "").strip()

            # 策略 1: 完全匹配（忽略大小写和空格）
            if normalize(animegarden_native) == title_norm:
                return animegarden_anime.get("air_time")

            # 策略 2: 包含匹配
            if (title_norm in normalize(animegarden_native) or
                normalize(animegarden_native) in title_norm):
                return animegarden_anime.get("air_time")

        return None

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
            "air_time": air_date,  # 默认使用 air_date，后续可能被 Anime Garden 覆盖
        }
