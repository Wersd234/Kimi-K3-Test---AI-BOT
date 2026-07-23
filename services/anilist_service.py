"""AniList GraphQL API 封装（真实动漫数据的唯一来源）。

提供：
- 动漫百科查询（海报、评分、简介、声优）
- 季度新番列表
- 追番更新检测（最新集数发布状态）
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

    async def search_anime(self, title: str) -> dict | None:
        """按标题搜索动漫，返回百科信息。

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
            description
            episodes
            status
            startDate {
              year
              month
              day
            }
            characters(sort: ROLE, perPage: 5) {
              nodes {
                name {
                  full
                }
                image {
                  medium
                }
              }
            }
          }
        }
        """
        try:
            data = await self._query(query, {"search": title})
            media = data.get("Media")
            if media:
                logger.info("AniList 查询成功: %s", media["title"]["romaji"])
            return media
        except Exception as exc:
            logger.error("AniList 查询失败: %s", exc)
            return None

    async def get_current_season(self, page: int = 1) -> list[dict]:
        """获取当前季度热门新番列表。

        Args:
            page: 分页页码。

        Returns:
            新番信息 dict 列表。
        """
        # 计算当前季度
        from datetime import datetime

        now = datetime.now()
        year = now.year
        month = now.month
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
          Page(page: $page, perPage: 10) {
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

    async def get_anime_status(self, anime_id: int) -> dict | None:
        """查询单部番剧的播出状态与最新集数（用于更新 Ping 轮询）。

        Args:
            anime_id: AniList 媒体 ID。

        Returns:
            包含 status / nextAiringEpisode 等字段的 dict。
        """
        query = """
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            id
            title {
              romaji
            }
            status
            episodes
            nextAiringEpisode {
              episode
              airingAt
            }
          }
        }
        """
        try:
            data = await self._query(query, {"id": anime_id})
            media = data.get("Media")
            if media:
                logger.info(
                    "AniList 状态查询成功: %s (status: %s)",
                    media["title"]["romaji"],
                    media["status"],
                )
            return media
        except Exception as exc:
            logger.error("AniList 状态查询失败: %s", exc)
            return None
