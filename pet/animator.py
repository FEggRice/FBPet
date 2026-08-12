"""Pure frame-stepping logic for one animation row. No GUI dependency."""


class SpriteAnimator:
    def __init__(self, frame_count: int, frame_ms: float, loop: bool):
        self.frame_count = frame_count
        self.frame_ms = frame_ms
        self.loop = loop
        self._elapsed = 0.0
        self.current_frame = 0
        self.is_done = False

    def advance(self, dt_ms: float) -> None:
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
        self._elapsed = 0.0
        self.current_frame = 0
        self.is_done = False
