# FB Pet — 桌宠开发路线图

## v1.0 — 已完成 ✓

| 功能 | 说明 |
|------|------|
| 双击 exe 启动 | .NET 8 WPF 单文件 |
| 透明置顶窗口 | `AllowsTransparency` + `Topmost` |
| 登场动画 + 启动音效 | spawn → idle 自动切换 |
| 待机动画循环 | 呼吸 + 眨眼 |
| 点击互动 | 点击 → 弹跳动画 + 音效 → 回待机 |
| 拖拽移动 | 按住拖到任意位置 |
| 右键隐藏到托盘 | 托盘图标 + 右键菜单退出 |
| JSON 配置换皮 | 改 `config.json` + 替换 `pet.png` + `audio/` |
| 占位素材自动生成 | 首次运行自动生成精灵表 + WAV |
| 全局按键计数 | `WH_KEYBOARD_LL` 钩子，按键位分别计数 + 总数 |
| 每 N 次休息提醒 | 每满阈值（默认 100）气泡 + 音效 + reminder 动画 |

## v1.x — 待完善

- [x] 窗口定位：读取实际屏幕尺寸，默认右下角
- [x] 打包单 exe：`dotnet publish -c Release -p:PublishSingleFile=true`
- [ ] 替换美术素材（精灵帧表 + 音效）
- [ ] 待机变体（打哈欠、坐下等随机触发）
- [ ] 托盘图标资源释放修复
- [ ] 开机自启选项

> 代码已存在（`FBPet/`），v1.0 + 按键提醒已可运行。核心逻辑有单元测试（`FBPet.Tests/`）。

## v2.0 — Agent 智能脑

- [ ] 预留 `IPetBrain` 接口
- [ ] Python FastAPI 后端（LLM 对话）
- [ ] 气泡文字显示
- [ ] 情绪 → 动画映射（happy/sad/angry → 切换动画）
- [ ] 定时行为（每到整点打招呼等）

## 项目结构

```
E:\桌面\FB\FBPet\
├── FBPet.csproj
├── config.json              # 动画 & 音频配置
├── App.xaml / App.xaml.cs
├── MainWindow.xaml           # 透明窗口定义
├── MainWindow.xaml.cs        # 窗口逻辑 + 状态机 + 输入
├── Models/
│   └── PetConfig.cs          # 配置数据模型
├── Core/
│   ├── SpriteAnimator.cs     # 精灵帧步进逻辑（纯逻辑，有测试）
│   ├── AudioManager.cs       # 音效管理
│   ├── AssetGenerator.cs     # 占位素材自动生成
│   ├── KeyCounter.cs         # 按键计数 + 每 N 次提醒（纯逻辑，有测试）
│   └── KeyboardHook.cs       # 全局 WH_KEYBOARD_LL 钩子
├── UI/
│   └── BubbleWindow.cs       # 休息提醒气泡（点击穿透）
└── bin/Debug/net8.0-windows/
    ├── FBPet.exe
    ├── config.json
    ├── pet.png               # 精灵帧表（1024×384, 128×128/cell）
    └── audio/
        ├── startup.wav
        └── click.wav
```

## 精灵帧表规格

| 行 | 动画 | 帧数 | FPS | 循环 |
|----|------|------|-----|------|
| 0 | idle | 4 | 6 | 是 |
| 1 | spawn | 6 | 10 | 否 |
| 2 | clicked | 5 | 12 | 否 |

每帧 128×128 像素，8 列 × 3 行 = 1024×384 PNG，透明背景。

## 如何换皮

1. 用你的精灵表替换 `pet.png`（保持相同规格，或改 `config.json` 里的尺寸）
2. 替换 `audio/` 下的 wav 文件（同名覆盖）
3. 修改 `config.json` 调整帧数、FPS、循环
4. 删掉旧 `pet.png` 和 `audio/` 再启动 → 自动重新生成占位素材（重置）

## 运行

```bash
cd E:\桌面\FB\FBPet
dotnet run                    # 开发
dotnet publish -c Release     # 发布单 exe
```
