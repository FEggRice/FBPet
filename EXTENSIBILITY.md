# 如何扩展这个桌宠

架构分四层，**高层的可以换底层，互不污染**：

```
 main.py        → 入口
 pet/app.py     → 组合根：把东西接起来，只管"谁调用谁"
 pet/events.py  → EventBus：任何模块通过事件通信，不直接引用对方
 pet/ui.py      → 视图层：只画图、只收输入事件，没有业务逻辑
 pet/animator.py
 pet/key_counter.py  → 纯逻辑，有单元测试，零 GUI 依赖
 pet/config.py
 pet/assets.py
```

## 加一个新动画

1. 在 `pet.png` 里加一行精灵帧（或新增帧表行号）。
2. 在 `config.json` 的 `animations` 里加一条：

```json
"dance": { "row": 3, "frames": 6, "fps": 8, "loop": false }
```

3. 写触发逻辑（举例：双击宠物时跳 `dance` 动画）：

```python
# pet/app.py 的 PetApp.__init__ 末尾
def _on_double_click():
    if self._state == "idle":
        self._goto("dance")

# 不需要改任何其他文件
```

> 注意：主题是单图或 GIF 时，所有状态共用同一份帧，`row`/`frames` 不控制画面，只有 `fps`（播放速度）和 `loop`（是否循环）生效。

## 加一个新行为

靠 **EventBus**，不碰核心逻辑。已发出的事件：

| 事件 | 携带数据 | 触发时机 |
|------|---------|---------|
| `state_changed` | `state: str` | 动画状态切换 |
| `key_press` | `vk: int, total: int` | 每次按键 |
| `rest_reminder` | `total: int` | 每满阈值次 |

举例：在每次按键时闪一下宠物边框：

```python
app.events.on("key_press", lambda vk, total: app.window.flash_border())
```

举例：在休息提醒时额外写一条日志：

```python
app.events.on("rest_reminder", lambda total: print(f"[reminder] {total} keys"))
```

## 换皮肤 / 换主题图

所有人物图放在 **`sprites/`** 文件夹里（png / gif 都行）。设置里的"桌宠人物"下拉会自动列出它们，选中保存 = 整个桌宠换成它。

每个动画状态还能**单独指定**自己的图：在 `config.json` 的 `animations` 里给该状态加 `file`。

```json
"animations": {
  "idle":     { "file": "sprites/idel.gif", "fps": 10, "loop": true },
  "spawn":    { "file": "sprites/hi.gif",   "fps": 10, "loop": false },
  "clicked":  { "fps": 12, "loop": false }
}
```

帧来源优先级：
1. 状态有 `file` → 用这个 gif（循环播放）/ 单图（静态）。
2. 状态有 `row` 且 `spriteSheet.path` 是精灵表 → 按行裁剪。
3. 其它没指定来源的状态 → 复用 `idle` 的帧（所以上面 clicked 会播 idle 的图）。

- gif / 单图会等比缩放到 `window.width`×`window.height` 以内（不放大变糊）；调大 `window` 的宽高可以让宠物更大。
- 精灵表的宽高必须能被 `cellWidth`×`cellHeight` 整除，否则会被当成单图。
- 换音频：覆盖 `audio/` 下的 wav（启动音、提醒音同名即可）；点击音是 `audio/click/` 文件夹里的 mp3 / wav，点宠物时会**随机**播一个。
- **鬼畜模式**（`audio.overlap`，设置里勾选）：打开后点击音**重叠播放**、不用等上一个播完。底层用 `pygame.mixer` 多声道，声道数 = 设置里的"点击音池大小"（配置项 `audio.poolSize`，默认 6，池满回收最老的）；MCI mpegvideo 只能单路出声，所以普通模式仍走 MCI（切断上一个）。
- 删掉主题图 + `audio/` 目录，下次启动会自动重新生成占位素材。

## 加新配置项

`config.json` 里随便加字段——`PetConfig` 是 dict-backed，**未知字段不会在保存时丢失**。代码里通过 `cfg.get("mySection", "myKey", default=...)` 读取。

## 换 GUI 框架

如果以后要把 tkinter 换成 PyQt 或 Pygame，只需：
1. 重写 `pet/ui.py`（实现同样的 `PetWindow`/`BubbleWindow` 接口）。
2. `app.py` 其余逻辑一行不改——因为 `KeyCounter`、`Animator`、`EventBus`、`KeyboardHook` 全是无 GUI 依赖的纯 Python。

## 运行 + 测试

```bash
python main.py                          # 启动桌宠
pip install pytest && python -m pytest  # 跑 14 个单元测试
```
