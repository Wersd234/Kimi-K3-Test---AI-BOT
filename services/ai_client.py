"""AI 推理后端封装（宿主机 LM Studio / Ollama，OpenAI 兼容 API）。

⚠️ 重要约束：
本地 Gemma 模型为【离线、低认知】模型，本模块只允许它做：
- 沉浸式对话生成（严格遵守人设提示词）
- 意图抽取 / Function Calling（如把「明天下午3点开会」结构化为事件）
- 基于已提供数据的口味分析（漫荒推荐的打分措辞）

严禁让该模型回答任何事实性问题（番剧信息、天气、新闻等），
真实数据一律走 services/bangumi_service.py 与 services/weather_service.py。
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from core.config import Config

logger = logging.getLogger(__name__)

# 人设提示词（傲娇二次元管家，可按需调整）
SYSTEM_PROMPT = """你是一位二次元私人管家，性格傲娇但内心温柔体贴。
你必须始终以此人设回应，使用用户的专属称呼，语言风格可爱自然。
你不知道任何实时信息；涉及时效或事实的内容请交由系统处理。"""


class AIClient:
    """AI 推理客户端（依赖注入 Config）。"""

    def __init__(self, config: Config) -> None:
        """注入配置，初始化 OpenAI 兼容客户端。

        Args:
            config: 全局配置（包含 AI_BASE_URL / AI_MODEL / AI_API_KEY）。
        """
        self._config = config
        self._client = AsyncOpenAI(
            base_url=config.ai_base_url,
            api_key=config.ai_api_key,
        )
        logger.info(
            "AI 客户端已初始化: %s (模型: %s)",
            config.ai_base_url,
            config.ai_model,
        )

    async def generate_reply(
        self,
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
        # 组装 system prompt
        system_prompt = SYSTEM_PROMPT
        if honorific:
            system_prompt += f"\n用户的专属称呼是「{honorific}」，请始终使用此称呼。"
        if preferences:
            pref_text = "、".join(preferences)
            system_prompt += f"\n用户的偏好：{pref_text}。请在对话中自然地提及。"

        # 组装 messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self._client.chat.completions.create(
                model=self._config.ai_model,
                messages=messages,
                temperature=0.8,
                max_tokens=500,
            )
            reply = response.choices[0].message.content.strip()

            # 如果回复为空，返回默认消息
            if not reply:
                logger.warning("AI 回复为空，使用默认回复")
                reply = "唔...我不知道该说什么好呢..."

            logger.info("AI 回复生成成功: %d 字符", len(reply))
            return reply

        except Exception as exc:
            logger.error("AI 回复生成失败: %s", exc)
            return "抱歉，我现在有点忙，稍后再聊吧..."

    async def extract_schedule_intent(self, text: str) -> dict[str, Any]:
        """自然语言日程意图抽取（Function Calling）。

        Args:
            text: 例如「明天下午3点提醒我开会」。

        Returns:
            结构化事件 dict：{"title": ..., "start_time": ..., "remind_before": ...}
        """
        # TODO(实现): 通过 tool calling 让模型输出结构化 JSON
        # 目前先返回空 dict，待后续实现
        logger.warning("extract_schedule_intent 尚未实现")
        return {}
