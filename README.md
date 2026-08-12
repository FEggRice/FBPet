# FBPet 桌面宠物

一个常驻桌面右下角的桌面宠物小应用：伴随动画播放，统计键盘使用量，长时间连续敲键盘时提醒休息，支持点击互动和系统托盘控制。

## 功能

- 桌面宠物动画（精灵图帧动画，闲置 / 出现 / 点击 / 提醒四种状态）
- 键盘按键次数统计
- 连续敲键盘休息提醒（可配置阈值与提示语）
- 系统托盘常驻（pystray）
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

## 打包

使用 PyInstaller：

```bash
pip install pyinstaller
pyinstaller FBPet.spec
```

产物在 `dist/` 目录下。

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
└── FBPet.spec         # PyInstaller 打包配置
```
