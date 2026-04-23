from cts.config import default_config
from cts.curriculum.scheduler import CurriculumTracker


def test_curriculum_blocks_promotion_without_window() -> None:
    cfg = default_config()
    tracker = CurriculumTracker(current_stage="stage1")
    for _ in range(cfg.stage1.promotion_window - 1):
        tracker.update(1.0, False)

    assert not tracker.can_promote(cfg)


def test_curriculum_requires_no_hold_flags() -> None:
    cfg = default_config()
    tracker = CurriculumTracker(current_stage="stage1")
    for _ in range(cfg.stage1.promotion_window):
        tracker.update(cfg.stage1.promotion_mean_reward + 0.1, True)

    assert not tracker.can_promote(cfg)


def test_curriculum_promotes_when_threshold_met() -> None:
    cfg = default_config()
    tracker = CurriculumTracker(current_stage="stage1")
    for _ in range(cfg.stage1.promotion_window):
        tracker.update(cfg.stage1.promotion_mean_reward + 0.1, False)

    assert tracker.can_promote(cfg)
    assert tracker.promote()
    assert tracker.current_stage == "stage2"
