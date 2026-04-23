from __future__ import annotations

from dataclasses import dataclass, field

from cts.config import TrialConfig


@dataclass
class CurriculumTracker:
    current_stage: str = "stage1"
    reward_history: list[float] = field(default_factory=list)
    safety_hold_history: list[bool] = field(default_factory=list)

    def update(self, reward: float, had_hold: bool) -> None:
        self.reward_history.append(reward)
        self.safety_hold_history.append(had_hold)

    def can_promote(self, config: TrialConfig) -> bool:
        stage = getattr(config, self.current_stage)
        window = stage.promotion_window
        if len(self.reward_history) < window:
            return False

        recent_rewards = self.reward_history[-window:]
        recent_holds = self.safety_hold_history[-window:]
        return (sum(recent_rewards) / window) >= stage.promotion_mean_reward and not any(recent_holds)

    def promote(self) -> bool:
        if self.current_stage == "stage1":
            self.current_stage = "stage2"
            return True
        if self.current_stage == "stage2":
            self.current_stage = "stage3"
            return True
        return False
