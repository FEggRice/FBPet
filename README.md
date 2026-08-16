# FBPet 桌面宠物 + FBeePet AI Agent —— 项目详细介绍

FBPet 是一个常驻桌面右下角的桌面宠物应用,在传统桌宠(动画、键盘计数、休息提醒、托盘、音效)的基础上,通过右键菜单「对话」集成 **FBeePet** —— 一个面向中文用户的轻量 AI Agent 框架与运行中枢,让桌宠变身 AI 助手的入口。

仓库由两部分组成,整体开源:

| 部分 | 说明 | 技术栈 |
| --- | --- | --- |
| **FBPet 桌宠** | 桌面宠物本体(仓库根目录) | Python + tkinter + pystray |
| **FBeePet** | 内置 AI Agent 框架与网页聊天界面(`FBeePet/`) | FastAPI + Vue 3 + SQLite |

![桌宠精灵原图 (sprites/pet_source.png, 2048×2048)](sprites/pet_source.png)

---

## 一、FBPet 桌面宠物

### 功能特性

- **角色动画**:闲置 idle / 出现 spawn / 点击 clicked / 提醒 reminder 四种状态,支持多套角色精灵图(`sprites/` 下 PNG/GIF,可在设置中切换)
- **键盘统计**:`WH_KEYBOARD_LL` 全局钩子按按键位计数,超阈值弹出休息提醒气泡(提示语可配置)
- **托盘常驻**:pystray 系统托盘,隐藏 / 恢复 / 退出
- **音效系统**:启动 / 点击 / 提醒音,通过 Windows MCI 播放 WAV 与 MP3,支持多音效叠加与并发播放池
- **右键径向轮盘菜单**:游戏化动效(弹簧展开、悬停放大发光、图标 + 中文标签),动作统一走 `on_context` 回调
- **右键「对话」**:拉起 FBeePet 服务并打开浏览器聊天界面
- **设置面板**:休息阈值、待机动画、音效、窗口缩放、计数器重置

### 架构设计

采用**组合根模式**(`pet/app.py`),把 配置 → 逻辑 → 视图 → 系统钩子 接线为一个可运行应用:

- **跨线程约定**:键盘钩子与托盘图标各自运行在独立线程,只向 `queue.Queue` 推送事件;tkinter 主线程通过 `_poll`(约 50ms)排空队列并分发,保证所有 tk 操作都在主线程执行
- **动画心跳**:`_tick`(约 16ms,≈60fps)按真实经过时间推进精灵帧
- **事件总线**:`pet/events.py` 的 `EventBus` 解耦键盘、动画、提醒等模块,任何模块通过事件通信、不直接相互引用
- **配置驱动**:`config.json` 为纯 JSON dict,未知字段在保存→加载往返中完整保留,新增动画/音效/设置无需改代码

### 模块清单

| 模块 | 职责 |
| --- | --- |
| `pet/app.py` | 组合根:装配全部模块、事件分发、生命周期 |
| `pet/agent.py` | FBeePet 子进程管理器(探活 / 启动 / 打开界面 / 退出终止) |
| `pet/animator.py` | 精灵帧动画推进(纯逻辑,可单测) |
| `pet/assets.py` | 角色发现与资源自动生成(占位精灵表 / WAV) |
| `pet/audio.py` | 音效注册与并发播放(MCI) |
| `pet/config.py` | JSON 配置薄封装 + 默认值 + agent 段深合并 |
| `pet/events.py` | 发布/订阅事件总线(扩展面) |
| `pet/frames.py` | 精灵表切帧与逐状态图片源解析 |
| `pet/key_counter.py` | 键盘计数与提醒判定(纯逻辑,可单测) |
| `pet/keyboard_hook.py` | 全局键盘钩子(独立线程 + 原生消息泵) |
| `pet/radial.py` | 径向轮盘几何与渲染(几何数学纯函数,可单测) |
| `pet/tray.py` | 系统托盘(pystray,独立线程) |
| `pet/ui.py` | 宠物窗口、气泡、设置对话框(纯视图层) |

### 配置说明(`config.json`)

| 键 | 说明 |
| --- | --- |
| `window` | 窗口尺寸、透明色、缩放 |
| `spriteSheet` / `animations` | 精灵图路径、帧布局、各动画行/帧数/帧率 |
| `audio` | 音效文件与播放池 |
| `rest` | 休息提醒阈值与提示语 |
| `countFile` | 键盘统计保存文件 |
| `agent` | 对话 Agent 的 host / port / python / dir(可选) |

`config.json` 是**本地个性化配置**(窗口尺寸、自定义精灵、可选的 `agent.python` 覆盖),已加入 `.gitignore` 不入库;首次运行自动生成默认配置。

---

## 二、FBeePet AI Agent 框架

### 定位

一个更加符合中文用户习惯的轻量级 AI Agent 框架,也是一个面向本地部署与长期运行的 AI Agent 中枢:

- **向上**连接 100+ LLM 提供商与不同模型策略(Anthropic / OpenAI / DeepSeek ...)
- **向外**连接 Web、微信、飞书、钉钉、Telegram、企业微信、QQ、微博、小智 AI 等入口
- **向内**组织角色、团队、工作流、记忆与安全边界
- **向执行层**连接文件、Shell、Web、屏幕、文件传输,以及 Claude Code、Codex、OpenCode 一类外部行业工具

一句话概括:**连接模型、渠道、团队和工具的 AI Agent 框架与运行中枢。**

### 核心能力

| 能力 | 说明 |
| --- | --- |
| 多智能体协作 | Agent Team,多角色分工、上下文衔接、团队级编排(pipeline / graph / council) |
| 技能系统 | 内置技能库,对话内完成 skills 搜索、安装、启用、禁用、删除 |
| MCP 客户端 | 多服务器连接、健康检查与工具发现 |
| Wiki 知识库 | BM25 全文搜索、批量获取、相关性过滤与 LRU 缓存 |
| 记忆系统 | 短期摘要缓存、溢出历史总结与整会话自动记忆沉淀 |
| 定时任务 | cron 调度与执行器,可配置主动问候与计划任务 |
| 多渠道接入 | 微信、飞书、钉钉、Telegram、企业微信、QQ、微博、小智 AI |
| 工具系统 | Shell、文件系统、Web、截图、文件传输、记忆、Wiki、工作流 |
| 外部编程工具 | Claude Code / Codex / OpenCode 适配,可作工具或代理接入 |
| 模型管理 | API Key 轮换与故障转移、思考强度控制 |
| WebSocket | 状态广播、流式输出、任务与工具调用实时通知 |

### 后端 API 一览

`FBeePet/backend/api/` 下 14 组路由:

| 前缀 | 职责 |
| --- | --- |
| `/api/chat` | 聊天、会话、消息、导出、任务 |
| `/api/agent-teams` | 多智能体团队编排 |
| `/api/channels` | 各渠道接入配置与状态 |
| `/api/cron` | 定时任务调度 |
| `/api/mcp` | MCP 服务器连接与工具发现 |
| `/api/memory` | 记忆管理与检索 |
| `/api/personalities` | 角色/人格管理 |
| `/api/queue` | 消息/任务队列 |
| `/api/settings` | 配置、提供商、外部编程工具、审计 |
| `/api/skills` | 技能库管理 |
| `/api/system` | 健康检查、状态、托盘 |
| `/api/tasks` | 任务管理 |
| `/api/tools` | 工具执行与注册 |
| `/api/wiki` | 知识库搜索与管理 |

### 前端模块

`FBeePet/frontend/`(Vue 3 + TypeScript + Vite,中英双语 i18n)按功能模块组织:`chat`(聊天界面)、`memory`(记忆编辑器/面板)、`scheduler`(定时任务)、`settings`(通用 / 模型 / 提供商 / 人格 / 工作区)、`skills`(技能库)、`system`(侧边栏)、`tools`(文件 / Shell / 工具历史)、`wiki`(知识库)。

### 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python、FastAPI、uvicorn、WebSocket、SQLite |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router |
| 集成 | MCP 协议、外部 CLI 工具适配 |

---

## 三、桌宠与 Agent 的集成

`pet/agent.py` 的 `AgentLauncher` 把 FBeePet 作为子进程托管:

1. **探活**:轮询 `http://127.0.0.1:8000`,服务已在跑则直接复用、不重复启动
2. **启动**:先运行 `seed_deepseek.py`(幂等地把默认模型固定为 deepseek-chat、清掉磁盘残留 Key),再以子进程启动 `uvicorn backend.app:app`,日志追加到 `FBeePet.log`
3. **打开界面**:后台线程轮询端口就绪后打开浏览器(`127.0.0.1:8000`)
4. **停止**:随桌宠退出用 `taskkill /T` 终止整个进程树

**安全设计**:DeepSeek API Key 由用户在网页端「设置 → 模型提供商」输入,只存于服务进程内存、不落盘,随桌宠退出一起清空;`data/`、`workspace/` 等运行时数据不入库。

---

## 四、运行与测试

```bash
# 桌宠(仓库根目录)
pip install -r requirements.txt
python main.py

# 对话 Agent 依赖(根目录执行,给右键「对话」用)
pip install -r FBeePet/requirements.txt

# 单元测试(桌宠,51 个用例;pytest.ini 排除 FBeePet/ 避免互相干扰)
pytest

# FBeePet 独立开发(在 FBeePet/ 目录)
python start_dev.py          # 后端
npm install && npm run dev   # 前端
```

### 开源使用说明

- 桌宠使用 PATH 上的 `python` 运行对话 Agent;若本机默认 Python 没装 fastapi / uvicorn,先执行上面的 `pip install -r FBeePet/requirements.txt`
- 若要指定某个虚拟环境,在本地 `config.json` 加一行即可(只写要覆盖的字段):`"agent": { "python": "C:\\your_venv\\Scripts\\python.exe" }`
- `config.json`、`FBeePet/data/`、`FBeePet/workspace/`、`*.log` 均已 `.gitignore`,本地设置与密钥不会上传

---

## 五、目录结构(概要)

```
├── main.py             # 桌宠入口
├── pet/                # 桌宠核心模块(组合根、动画、键盘钩子、托盘、轮盘、AgentLauncher)
├── audio/              # 点击 / 提醒音效
├── sprites/            # 精灵图与角色原图(pet_source.png 为 2048×2048 原图)
├── tests/              # 桌宠单元测试(pytest)
├── FBeePet/            # 内置 AI 对话 Agent(FastAPI 后端 + Vue3 前端)
│   ├── backend/api/    #   路由:chat / channels / cron / mcp / skills / wiki ...
│   ├── backend/modules/ #  业务模块:agent / providers / tools / channels / mcp / cron ...
│   ├── frontend/       #   Vue3 前端(含 dist/ 构建产物)
│   ├── resources/      #   图标
│   └── seed_deepseek.py / start_*.py
└── config.json         # 本地个性化配置(已 gitignore,不入库)
```

---

## 六、开发方向建议

- **桌宠侧**:更多互动动画状态、天气/日程等 Widget、宠物养成机制
- **Agent 侧**:接入更多工具与渠道、强化多智能体协作场景、优化记忆与上下文压缩成本
- **联动**:把桌宠的键盘计数、休息提醒与 Agent 的能力结合,如"用语音/文字向桌宠下达休息或工作指令"
