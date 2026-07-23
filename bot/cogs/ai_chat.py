"""AI 闲聊与人设对话模块 [🌐 公开 / 🔒 私密]。

功能：
- 群组 @管家 或私聊触发沉浸式对话（严格遵守二次元人设）
- 短期上下文记忆（最近 10-20 轮）
- 私聊中自动捕捉长期偏好（RAG）

注意：本模块只负责收发消息，对话生成逻辑在 services/ai_client.py。
"""

from discord.ext import commands

from services import ai_client, memory


class AIChatCog(commands.Cog, name="AIChat"):
    """AI 交互与人设系统。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        """监听消息：私聊或群组 @ 时触发管家回复。"""
        # TODO(实现):
        # 1. 过滤机器人自身消息
        # 2. 判断触发条件（DM 或 mentions 包含本 Bot）
        # 3. 从 memory 读取上下文与专属称呼
        # 4. 调用 ai_client.generate_reply() 生成回复
        # 5. 回复消息并把本轮对话写回 memory
        pass


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(AIChatCog(bot))
