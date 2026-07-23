"""AI 闲聊与人设对话模块 [🌐 公开 / 🔒 私密]。

功能：
- 群组 @管家 或私聊触发沉浸式对话（严格遵守二次元人设）
- 短期上下文记忆（最近 10-20 轮）
- 私聊中自动捕捉长期偏好（RAG）
"""

import logging

from discord.ext import commands

from services import memory

logger = logging.getLogger(__name__)


class AIChatCog(commands.Cog, name="AIChat"):
    """AI 交互与人设系统。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        """监听消息：私聊或群组 @ 时触发管家回复。"""
        # 过滤机器人自身消息
        if message.author.bot:
            return

        # 判断触发条件（DM 或 mentions 包含本 Bot）
        is_dm = message.guild is None
        is_mentioned = self.bot.user in message.mentions

        if not (is_dm or is_mentioned):
            return

        user_id = message.author.id
        user_message = message.content.strip()

        # 移除 @ 机器人的部分
        if is_mentioned:
            user_message = user_message.replace(f"<@{self.bot.user.id}>", "").strip()

        if not user_message:
            await message.reply("有什么我可以帮你的吗？")
            return

        try:
            # 从 memory 读取上下文与专属称呼
            honorific = await memory.get_honorific(user_id)
            history = await memory.get_history(user_id)
            preferences = await memory.get_preferences(user_id)

            # 调用 AI 生成回复
            ai_client = self.bot.services.ai_client
            reply = await ai_client.generate_reply(
                user_message,
                history,
                honorific=honorific,
                preferences=preferences,
            )

            # 回复消息
            await message.reply(reply)

            # 把本轮对话写回 memory
            await memory.append_history(user_id, "user", user_message)
            await memory.append_history(user_id, "assistant", reply)

            logger.info("用户 %s 的 AI 对话已处理", user_id)

        except Exception as exc:
            logger.error("AI 对话处理失败: %s", exc)
            await message.reply("抱歉，我现在有点忙，稍后再聊吧...")


async def setup(bot: commands.Bot) -> None:
    """Cog 加载入口。"""
    await bot.add_cog(AIChatCog(bot))
