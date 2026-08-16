# FBPet 桌面宠物

一个常驻桌面右下角的桌面宠物小应用：伴随动画播放，统计键盘使用量，长时间连续敲键盘时提醒休息，支持点击互动和系统托盘控制。

## 功能

- 桌面宠物动画（精灵图帧动画，闲置 / 出现 / 点击 / 提醒四种状态）
- 键盘按键次数统计
- 连续敲键盘休息提醒（可配置阈值与提示语）
- 系统托盘常驻（pystray）
- 右键径向轮盘菜单（游戏化动效：弹簧展开、悬停放大发光、图标 + 悬停中文标签）
- 启动 / 点击 / 提醒音效

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 配置

配置文件 `config.json`（首次运行自动生成）：

- `window`：窗口尺寸与透明色
- `spriteSheet`：精灵图路径与帧布局（8 列 3 行）
- `animations`：各动画的行、帧数、帧率与是否循环
- `audio`：音效文件路径
- `rest`：休息提醒阈值与提示语
- `countFile`：键盘统计保存文件
- `agent`：对话 Agent 的 host / port / python / dir（可选）

## 对话（FBeePet Agent）

右键菜单「对话」拉起内置的 FBeePet 网页 Agent（FastAPI + Vue3），浏览器打开 http://127.0.0.1:8000。

需要 Python 装有 `fastapi` / `uvicorn`：

```bash
pip install -r FBeePet/requirements.txt
```

默认使用 PATH 上的 `python` 运行；若要指定某个虚拟环境，在本地 `config.json` 里加一行即可（只写要覆盖的字段）：

```json
"agent": { "python": "C:\\your_venv\\Scripts\\python.exe" }
```

`config.json` 已在 .gitignore 中，不会提交到仓库。

## 测试

```bash
pytest
```

## 目录结构

```
├── main.py            # 入口
├── pet/               # 核心模块（应用、动画、键盘钩子、托盘等）
├── audio/             # 音效资源
├── tests/             # 单元测试
├── top.png            # 宠物精灵图
└── start.bat          # 启动脚本（python main.py）
```
