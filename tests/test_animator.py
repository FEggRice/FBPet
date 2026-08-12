from pet.animator import SpriteAnimator


def test_advance_steps_through_frames():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=True)
    a.advance(100)
    assert a.current_frame == 1
    a.advance(100)
    assert a.current_frame == 2
    a.advance(100)
    assert a.current_frame == 3


def test_advance_loops_back_to_first_frame():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=True)
    for _ in range(4):
        a.advance(100)
    assert a.current_frame == 0
    assert a.is_done is False


def test_advance_does_not_cross_frame_before_boundary():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=True)
    a.advance(99)
    assert a.current_frame == 0
    a.advance(1)
    assert a.current_frame == 1


def test_advance_handles_large_delta_across_frames():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=True)
    a.advance(250)
    assert a.current_frame == 2


def test_advance_non_looping_stops_at_last_frame():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=False)
    a.advance(300)
    assert a.current_frame == 3
    a.advance(500)
    assert a.current_frame == 3
    assert a.is_done is True


def test_reset_restores_first_frame_and_clears_done():
    a = SpriteAnimator(frame_count=4, frame_ms=100, loop=False)
    a.advance(1000)
    assert a.is_done is True

    a.reset()

    assert a.current_frame == 0
    assert a.is_done is False
