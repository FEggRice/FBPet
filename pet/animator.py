"""Pure frame-stepping logic for one animation row. No GUI dependency."""


class SpriteAnimator:
    # 单行动画帧推进器：只管"经过多少毫秒 → 显示第几帧"，与 GUI 无关

    def __init__(self, frame_count: int, frame_ms: float, loop: bool):
        # 初始化：总帧数、每帧毫秒数、是否循环；当前帧从 0 开始、未播完
        self.frame_count = frame_count
        self.frame_ms = frame_ms
        self.loop = loop
        self._elapsed = 0.0
        self.current_frame = 0
        self.is_done = False

    def advance(self, dt_ms: float) -> None:
        # 推进动画：累加经过时间，算出当前该显示第几帧；
        # 循环动画取模回绕，非循环动画播完停在最后一帧并标记 is_done
        if self.is_done:
            return
        self._elapsed += dt_ms
        frame = int(self._elapsed / self.frame_ms)
        if self.loop:
            self.current_frame = frame % self.frame_count
        elif frame >= self.frame_count:
            self.current_frame = self.frame_count - 1
            self.is_done = True
        else:
            self.current_frame = frame

    def reset(self) -> None:
        # 重置回初始状态：清零计时、帧回到 0、清除播完标记
        self._elapsed = 0.0
        self.current_frame = 0
        self.is_done = False
