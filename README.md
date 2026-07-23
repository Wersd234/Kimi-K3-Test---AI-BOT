# 二次元私人管家 Discord Bot

一个以「二次元私人管家」为人设的 Discord Bot，提供 AI 闲聊、追番管理、
日程提醒与每日简报等私密化服务。

## 架构总览

```
┌────────────────────────────────────────────────┐
│  Discord 前端层 (bot/)                          │
│  仅负责事件监听 / 斜杠指令 / 按钮与表单 UI        │
│  不包含任何 AI 推理与外部数据查询逻辑              │
└───────────────┬────────────────────────────────┘
                │ 调用服务接口
┌───────────────▼────────────────────────────────┐
│  服务层 (services/)                             │
│  ai_client   → 宿主机 LM Studio (Gemma，OpenAI 兼容 API)
│  anilist     → AniList GraphQL（真实动漫数据）    │
│  weather     → Open-Meteo（真实天气数据）         │
│  memory      → 对话上下文 / 长期偏好 / 专属称呼    │
│  calendar    → 日程事件的存储与到期查询            │
└───────────────┬────────────────────────────────┘
                │ 读写
┌───────────────▼────────────────────────────────┐
│  核心层 (core/)                                 │
│  config     → .env 配置集中管理                  │
│  database   → SQLite (aiosqlite)，Volume 落盘    │
│  scheduler  → APScheduler 定时任务               │
└────────────────────────────────────────────────┘
```

> ⚠️ 重要设计原则：本地 Gemma 模型为**离线低认知模型**，
> 只负责「对话生成、人设扮演、意图抽取（Function Calling）」，
> **绝不承担事实性内容查询**。所有真实数据（番剧、天气）一律走第三方 API。

## 目录结构

```
MyDiscordBot/
├── Dockerfile              # Bot 镜像构建
├── docker-compose.yml      # 容器编排（含 Volume 挂载与时区）
├── requirements.txt
├── .env.example            # 环境变量模板（复制为 .env 后填写）
├── core/                   # 核心基础设施
│   ├── config.py           #   配置加载
│   ├── database.py         #   SQLite 连接与建表
│   └── scheduler.py        #   定时任务调度
├── bot/                    # Discord 前端层
│   ├── main.py             #   入口
│   ├── client.py           #   Bot 客户端（加载 Cogs / 同步指令）
│   ├── cogs/               #   指令模块（ai_chat / anime / schedule / persona）
│   ├── ui/                 #   交互组件（按钮 / 表单）
│   └── utils/              #   展示工具（Embed 渲染等）
├── services/               # 服务层（AI / AniList / 天气 / 记忆 / 日历）
└── data/                   # SQLite 数据库落盘目录（Docker Volume 挂载点）
```

## 快速开始

```bash
cp .env.example .env   # 填入你的 DISCORD_TOKEN 等配置
docker compose up -d --build
```

## 开发路线图

- [x] 项目文件架构搭建（当前阶段）
- [ ] 核心层实现：配置加载 / 数据库建表 / 调度器
- [ ] AI 服务封装：OpenAI 兼容客户端 + 人设提示词 + Function Calling
- [ ] AniList / 天气服务封装
- [ ] Discord Cogs：AI 闲聊、动漫查询、日程管理、人设设定
- [ ] 定时任务：早安简报 / 更新 Ping / 防熬夜提醒
