"""AniList GraphQL API 封装（用于获取实际播出时间）。

提供：
- 番剧播出状态查询（nextAiringEpisode 包含具体播出时间）
- 与 Bangumi 结合使用（Bangumi 提供中文标题，AniList 提供播出时间）

API 文档：https://anilist.gitbook.io/anilist-apiv2-docs/
"""

import logging
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

    async def get_anime_airing_time(self, title: str) -> str | None:
        """按标题搜索番剧，获取下一集播出时间。

        Args:
            title: 番剧名称（支持中文/日文/英文）。

        Returns:
            播出时间字符串（如 "2026-07-25 15:30"），未找到返回 None。
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
            status
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
                logger.warning("AniList 查询无结果: %s", title)
                return None

            next_episode = media.get("nextAiringEpisode")
            if not next_episode:
                logger.info("番剧已完结或无下一集信息: %s", title)
                return None

            # airingAt 是 Unix 时间戳（秒）
            airing_timestamp = next_episode.get("airingAt")
            if not airing_timestamp:
                return None

            # 转换为本地时间
            from datetime import datetime

            airing_time = datetime.fromtimestamp(airing_timestamp)
            time_str = airing_time.strftime("%Y-%m-%d %H:%M")

            logger.info(
                "AniList 播出时间查询成功: %s → %s",
                media["title"]["romaji"],
                time_str,
            )
            return time_str

        except Exception as exc:
            logger.error("AniList 播出时间查询失败: %s", exc)
            return None

    async def get_current_season(self, page: int = 1) -> list[dict]:
        """获取当前季度热门新番列表（包含播出时间）。

        Args:
            page: 分页页码。

        Returns:
            新番信息 dict 列表（包含 nextAiringEpisode）。
        """
        from datetime import datetime

        now = datetime.now()
        year = now.year
        month = now.month

        # 计算当前季度
        if 1 <= month <= 3:
            season = "WINTER"
        elif 4 <= month <= 6:
            season = "SPRING"
        elif 7 <= month <= 9:
            season = "SUMMER"
        else:
            season = "FALL"

        query = """
        query ($season: MediaSeason, $seasonYear: Int, $page: Int) {
          Page(page: $page, perPage: 50) {
            media(season: $season, seasonYear: $seasonYear, type: ANIME, sort: POPULARITY_DESC) {
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
              airingSchedule(perPage: 1) {
                nodes {
                  episode
                  airingAt
                }
              }
            }
          }
        }
        """
        try:
            data = await self._query(
                query,
                {"season": season, "seasonYear": year, "page": page},
            )
            media_list = data.get("Page", {}).get("media", [])
            logger.info("AniList 季度查询成功: %d 部新番", len(media_list))
            return media_list
        except Exception as exc:
            logger.error("AniList 季度查询失败: %s", exc)
            return []
