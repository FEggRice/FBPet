# FBPet 项目分析

> 本文档对 FBPet 桌面宠物及其内嵌的 FBeePet AI Agent 框架进行整体分析。

![FBPet 宠物形象素材](sprites/pet_source.png)

---

## 项目总览

FBPet 是一个常驻桌面右下角的桌面宠物应用，在传统桌宠（动画、键盘计数、休息提醒、托盘、音效）的基础上，通过右键菜单的「对话」入口集成了 **FBeePet** —— 一个面向中文用户的开源 AI Agent 框架与运行中枢，让桌宠变身 AI 助手的入口。

仓库由两部分组成：

| 部分 | 说明 |
| --- | --- |
| **FBPet 桌宠** | Python + tkinter 桌面宠物（根目录） |
| **FBeePet** | AI Agent 框架，FastAPI 后端 + Vue3 前端（`FBeePet/` 目录） |

---

## 一、FBPet 桌面宠物

### 功能特性

- 桌面宠物动画：闲置（idle）/ 出现（spawn）/ 点击（clicked）/ 提醒（reminder）四种状态，支持多套角色精灵图（`sprites/` 下的 PNG/GIF，可在设置中切换）
- 全局键盘按键计数，超过阈值自动弹出休息提醒气泡（提示语可配置）
- 系统托盘常驻（pystray），可隐藏/显示/退出
- 音效系统：启动 / 点击 / 提醒音，支持多音效叠加（"鬼畜模式"）与并发播放池
- 设置面板：修改休息阈值、待机动画、音效、窗口缩放、计数器重置
- 右键菜单「对话」：拉起 FBeePet 服务并打开浏览器聊天界面

### 架构设计

采用组合根模式（`pet/app.py`），将配置 → 逻辑 → 视图 → 系统钩子接线为一个可运行的应用：

- **跨线程约定**：键盘钩子与托盘图标各自运行在线程中，只向队列（`queue.Queue`）推送事件；tkinter 主线程通过 `_poll`（50ms 周期）排空队列并分发，保证所有 tk 操作都在主线程执行
- **动画心跳**：`_tick`（16ms 周期，约 60fps）按真实经过时间推进精灵图帧
- **事件总线**：`EventBus` 解耦键盘、动画、提醒等模块
- **配置驱动**：`config.json` 为纯 JSON dict，未知字段在保存→加载往返中完整保留，新增动画/音效/设置无需改代码

### 模块清单

| 模块 | 职责 |
| --- | --- |
| `pet/app.py` | 组合根：装配全部模块、事件分发、生命周期 |
| `pet/agent.py` | FBeePet 子进程管理器（探活/启动/打开界面/退出） |
| `pet/animator.py` | 精灵图帧动画推进 |
| `pet/assets.py` | 角色发现与资源自动生成（占位精灵图/WAV） |
| `pet/audio.py` | 音效注册与并发播放 |
| `pet/config.py` | JSON 配置的薄封装与默认值 |
| `pet/events.py` | 事件总线 |
| `pet/frames.py` | 精灵表切帧 |
| `pet/key_counter.py` | 键盘计数与提醒判定 |
| `pet/keyboard_hook.py` | 全局键盘钩子（线程） |
| `pet/tray.py` | 系统托盘（线程） |
| `pet/ui.py` | 宠物窗口、气泡、设置对话框 |

---

## 二、FBeePet AI Agent 框架

### 定位

FBeePet 是一个更加符合中文用户习惯的轻量级 AI Agent 框架，也是一个面向本地部署与长期运行的 AI Agent 中枢（v0.9.0，MIT 协议）：

- **向上**连接 100+ LLM 提供商与不同模型策略
- **向外**连接 Web、微信、飞书、钉钉、Telegram、企业微信、QQ、微博等入口
- **向内**组织角色、团队、工作流、记忆与安全边界
- **向执行层**连接文件、Shell、Web、屏幕、文件传输，以及 Claude Code、Codex、OpenCode 一类外部行业工具

一句话概括：**连接模型、渠道、团队和工具的 AI Agent 框架与运行中枢。**

### 核心能力

| 能力 | 说明 |
| --- | --- |
| 多智能体协作 | Agent Team，支持多角色分工、上下文衔接与团队级编排（pipeline / graph / council） |
| 技能系统 | 内置技能库，支持对话完成 skills 的搜索、安装、启用、禁用与删除（可接腾讯云 SkillsHub） |
| MCP 客户端 | 多服务器连接、健康检查与工具发现（v0.9.0 新增） |
| Wiki 知识库 | 基于 BM25 全文搜索，支持批量获取、相关性过滤与 LRU 缓存（v0.9.0 新增） |
| 记忆系统 | 短期摘要缓存、溢出历史总结与整会话自动记忆沉淀 |
| 定时任务 | cron 调度与执行器，可配置主动问候与计划任务 |
| 多渠道接入 | 微信、飞书、钉钉、Telegram、企业微信、QQ、微博、小智 AI |
| 工具系统 | Shell、文件系统、Web、截图、文件传输、记忆、Wiki、工作流等 |
| 外部编程工具 | Claude Code / Codex / OpenCode 适配，可作为工具或代理接入 |
| 模型管理 | 100+ LLM 提供商，API Key 轮换与故障转移，思考强度控制 |
| WebSocket | 状态广播、流式输出、任务与工具调用实时通知 |

### 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.8+、FastAPI、uvicorn、WebSocket、SQLite |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router（中英双语 i18n） |
| 集成 | MCP 协议、外部 CLI 工具适配 |

### 目录结构（关键）

```
FBeePet/
├── backend/              # FastAPI 后端
│   ├── api/              # 路由层：chat / channels / cron / mcp / skills / wiki ...
│   ├── models/           # 数据模型：agent_team / message / personality / task ...
│   ├── modules/          # 业务模块
│   │   ├── agent/        #   多智能体、技能、记忆、工作流、子代理
│   │   ├── channels/     #   微信 / 飞书 / 钉钉 / Telegram / 企微 / QQ / 微博 / 小智
│   │   ├── providers/    #   LLM 提供商（Anthropic / OpenAI / DeepSeek ...）
│   │   ├── tools/        #   Shell / 文件系统 / Web / 截图 / 工作流 ...
│   │   ├── mcp/          #   MCP 客户端
│   │   ├── cron/         #   定时任务
│   │   ├── wiki/         #   知识库
│   │   └── session/      #   会话与上下文管理
│   └── utils/ ws/        # 工具与 WebSocket
├── frontend/             # Vue 3 前端（chat / memory / scheduler / settings / skills / wiki / tools）
├── resources/            # 图标资源
├── seed_deepseek.py      # 初始化脚本（固定默认模型、清理残留 Key）
└── start_app.py / start_dev.py / start_desktop.py
```

---

## 三、桌宠与 Agent 的集成

`pet/agent.py` 中的 `AgentLauncher` 把 FBeePet 作为子进程托管：

1. **探活**：轮询 `http://127.0.0.1:8000`，服务已在跑则直接复用
2. **启动**：先运行 `seed_deepseek.py`（幂等地把默认模型固定为 deepseek-chat、清掉磁盘上残留的 API Key），再以子进程启动 `uvicorn backend.app:app`，日志追加到 `FBeePet.log`
3. **打开界面**：后台线程轮询端口就绪后打开浏览器（`127.0.0.1:8000`）
4. **停止**：随桌宠退出用 `taskkill /T` 终止整个进程树

安全设计：DeepSeek API Key 由用户在网页端「设置 → 模型提供商」输入，只存于服务进程内存、不落盘，随桌宠退出一起清空。桌宠的 `pytest.ini` 明确排除 `FBeePet/`，避免测试互相干扰。

---

## 四、运行与测试

```bash
# 桌宠
pip install -r requirements.txt
python main.py

# 单元测试（仅桌宠，不含 FBeePet）
pytest

# FBeePet 独立开发（在 FBeePet/ 目录）
python start_dev.py        # 后端
npm install && npm run dev # 前端
```

---

## 五、开发方向建议

- **桌宠侧**：更多互动动画状态、天气/日程等 Widget、宠物养成机制
- **Agent 侧**：接入更多工具与渠道、强化多智能体协作场景、优化记忆与上下文压缩成本
- **联动**：把桌宠的键盘计数、休息提醒与 Agent 的能力结合，如"用语音/文字向桌宠下达休息或工作指令"
