"""天气 API 封装（Open-Meteo，免费免密钥）。

仅用于每日早安简报中的今日天气预报。
"""

import aiohttp

from core.config import config


async def get_today_weather() -> dict:
    """获取默认坐标城市的今日天气预报。

    Returns:
        包含温度区间、天气状况、降水概率等字段的 dict。
    """
    # TODO(实现): 调用 Open-Meteo forecast 接口，取 daily 数据
    raise NotImplementedError
