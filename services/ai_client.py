"""AI 推理后端封装（宿主机 LM Studio / Ollama，OpenAI 兼容 API）。

⚠️ 重要约束：
本地 Gemma 模型为【离线、低认知】模型，本模块只允许它做：
- 沉浸式对话生成（严格遵守人设提示词）
- 意图抽取 / Function Calling（如把「明天下午3点开会」结构化为事件）
- 基于已提供数据的口味分析（漫荒推荐的打分措辞）

严禁让该模型回答任何事实性问题（番剧信息、天气、新闻等），
真实数据一律走 services/anilist_service.py 与 services/weather_service.py。

TODO(依赖注入): 实现时改为接收 Config 参数，而非读取全局配置。
"""

# TODO(实现): 待实现时改为依赖注入模式
# from openai import AsyncOpenAI
# from core.config import Config

# _client = AsyncOpenAI(
#     base_url=config.ai_base_url,
#     api_key=config.ai_api_key,
# )

# 人设提示词（傲娇二次元管家，可按需调整）
SYSTEM_PROMPT = """你是一位二次元私人管家，性格傲娇但内心温柔体贴。
你必须始终以此人设回应，使用用户的专属称呼，语言风格可爱自然。
你不知道任何实时信息；涉及时效或事实的内容请交由系统处理。"""


async def generate_reply(
    user_message: str,
    history: list[dict],
    honorific: str | None = None,
    preferences: list[str] | None = None,
) -> str:
    """生成沉浸式闲聊回复。

    Args:
        user_message: 用户本轮消息。
        history: 短期上下文（最近 10-20 轮，OpenAI messages 格式）。
        honorific: 专属称呼（如「主人」）。
        preferences: 长期偏好记忆条目（RAG 检索结果）。

    Returns:
        管家的回复文本。
    """
    # TODO(实现): 组装 system prompt + history + user_message 调用模型
    raise NotImplementedError


async def extract_schedule_intent(text: str) -> dict:
    """自然语言日程意图抽取（Function Calling）。

    Args:
        text: 例如「明天下午3点提醒我开会」。

    Returns:
        结构化事件 dict：{"title": ..., "start_time": ..., "remind_before": ...}
    """
    # TODO(实现): 通过 tool calling 让模型输出结构化 JSON
    raise NotImplementedError
