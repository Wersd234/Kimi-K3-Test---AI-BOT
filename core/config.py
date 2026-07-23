"""集中管理所有环境变量配置（Pure Fabrication + Factory Method）。

设计说明：
- Config 为冻结 dataclass，实例化后不可变，防止运行时被意外修改。
- 通过 from_env() 工厂方法显式加载，解析失败立即抛错（fail-fast），
  避免模块级隐式加载产生晦涩的 ImportError。
- 提供 validate_required() 启动校验，缺失关键凭证时给出清晰报错。
- 业务代码中禁止直接调用 os.getenv，统一经由本模块读取配置。
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# 默认数据库路径（开发环境），生产环境由 .env 的 DATABASE_PATH 覆盖
_DEFAULT_DB_PATH = "./data/butler.db"


@dataclass(frozen=True)
class Config:
    """全局配置对象（只读）。"""

    # ── Discord ──────────────────────────────────────────
    discord_token: str
    dev_guild_id: int | None

    # ── AI 推理后端（宿主机 LM Studio / Ollama）────────────
    ai_base_url: str
    ai_model: str
    ai_api_key: str

    # ── 第三方 API ───────────────────────────────────────
    anilist_api_url: str
    weather_api_url: str
    weather_lat: float
    weather_lon: float

    # ── 运行环境 ─────────────────────────────────────────
    timezone: str
    database_path: str

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "Config":
        """工厂方法：从环境变量（及 .env 文件）构建配置实例。

        Args:
            env_file: .env 文件路径；None 表示自动从当前目录查找。

        Returns:
            解析完成的 Config 实例。

        Raises:
            ValueError: 数值型环境变量格式非法时（fail-fast）。
        """
        load_dotenv(env_file)

        # 可选整型：未设置或为空字符串都视为 None
        raw_guild_id = os.getenv("DEV_GUILD_ID") or ""
        try:
            dev_guild_id = int(raw_guild_id) if raw_guild_id.strip() else None
        except ValueError as exc:
            raise ValueError(
                f"环境变量 DEV_GUILD_ID 必须是整数，当前值: {raw_guild_id!r}"
            ) from exc

        # 浮点型坐标：格式非法时 fail-fast
        try:
            weather_lat = float(os.getenv("WEATHER_LAT", "-33.8688"))
            weather_lon = float(os.getenv("WEATHER_LON", "151.2093"))
        except ValueError as exc:
            raise ValueError(
                "环境变量 WEATHER_LAT / WEATHER_LON 必须是数字"
            ) from exc

        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            dev_guild_id=dev_guild_id,
            ai_base_url=os.getenv(
                "AI_BASE_URL", "http://host.docker.internal:1234/v1"
            ),
            ai_model=os.getenv("AI_MODEL", "google/gemma-4"),
            ai_api_key=os.getenv("AI_API_KEY", "not-needed-for-local"),
            anilist_api_url=os.getenv(
                "ANILIST_API_URL", "https://graphql.anilist.co"
            ),
            weather_api_url=os.getenv(
                "WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast"
            ),
            weather_lat=weather_lat,
            weather_lon=weather_lon,
            timezone=os.getenv("TZ", "Australia/Sydney"),
            database_path=os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH),
        )

    def validate_required(self) -> None:
        """校验启动必需的关键配置。

        Raises:
            RuntimeError: 缺少关键配置时，附带可读的错误信息。
        """
        if not self.discord_token:
            raise RuntimeError(
                "缺少 DISCORD_TOKEN：请复制 .env.example 为 .env 并填写 Token"
            )


def load_config(env_file: str | None = None) -> Config:
    """模块级便捷入口：加载并返回配置实例。

    供组合根（main.py）与测试脚本调用；业务模块应通过参数
    接收 Config 而非反复调用本函数（显式依赖）。
    """
    return Config.from_env(env_file)
