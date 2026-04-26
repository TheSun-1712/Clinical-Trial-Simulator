"""Multi-site clinical trial operations manager."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List


# Pre-defined site pool with realistic geographic distribution
SITE_POOL = [
    {"country": "United States", "city": "Boston",       "coords": [-71.1, 42.4],  "tier": "academic"},
    {"country": "United States", "city": "Houston",      "coords": [-95.4, 29.7],  "tier": "academic"},
    {"country": "United States", "city": "Chicago",      "coords": [-87.6, 41.9],  "tier": "community"},
    {"country": "United Kingdom","city": "London",       "coords": [-0.1,  51.5],  "tier": "academic"},
    {"country": "Germany",       "city": "Berlin",       "coords": [13.4,  52.5],  "tier": "academic"},
    {"country": "France",        "city": "Paris",        "coords": [2.3,   48.9],  "tier": "community"},
    {"country": "India",         "city": "Mumbai",       "coords": [72.9,  19.1],  "tier": "community"},
    {"country": "Japan",         "city": "Tokyo",        "coords": [139.7, 35.7],  "tier": "academic"},
    {"country": "Australia",     "city": "Sydney",       "coords": [151.2, -33.9], "tier": "academic"},
    {"country": "Brazil",        "city": "São Paulo",    "coords": [-46.6, -23.5], "tier": "community"},
    {"country": "Canada",        "city": "Toronto",      "coords": [-79.4, 43.7],  "tier": "academic"},
    {"country": "South Korea",   "city": "Seoul",        "coords": [126.9, 37.6],  "tier": "academic"},
    {"country": "Netherlands",   "city": "Amsterdam",    "coords": [4.9,   52.4],  "tier": "community"},
    {"country": "Spain",         "city": "Barcelona",    "coords": [2.2,   41.4],  "tier": "community"},
    {"country": "Switzerland",   "city": "Basel",        "coords": [7.6,   47.6],  "tier": "academic"},
]


@dataclass
class ClinicalSite:
    site_id: str
    country: str
    city: str
    coords: List[float]        # [lng, lat]
    tier: str                   # academic | community
    activation_week: int = 0
    status: str = "pending"     # pending | active | on_hold | closed
    enrolled_count: int = 0
    screen_failure_rate: float = 0.0
    protocol_deviations: int = 0
    performance_score: float = 1.0  # 1.0 = perfect, <0.6 = underperforming
    recruitment_rate: float = 0.0   # patients/week
    last_deviation_week: int = -1

    def activate(self, week: int, rng: random.Random) -> None:
        self.status = "active"
        self.activation_week = week
        # Academic centres recruit faster; community sites have more screen failures
        base_rate = 1.8 if self.tier == "academic" else 0.9
        self.recruitment_rate = max(0.1, rng.gauss(base_rate, 0.3))
        self.screen_failure_rate = rng.uniform(0.10, 0.35)
        self.performance_score = rng.uniform(0.75, 1.0)

    def step(self, week: int, rng: random.Random) -> int:
        """Simulate one week of site recruitment. Returns new patients enrolled."""
        if self.status != "active":
            return 0
        # Performance drift
        self.performance_score = min(1.0, max(0.3, self.performance_score + rng.gauss(0, 0.01)))
        # Random protocol deviation
        if rng.random() < 0.03:
            self.protocol_deviations += 1
            self.last_deviation_week = week
            if self.protocol_deviations >= 5:
                self.status = "on_hold"
                return 0
        import numpy as np
        _seed = rng.randint(0, 2**31)
        recruited = int(np.random.default_rng(_seed).poisson(max(0.1, self.recruitment_rate * self.performance_score)))


        screen_failed = int(recruited * self.screen_failure_rate)
        enrolled = max(0, recruited - screen_failed)
        self.enrolled_count += enrolled
        return enrolled

    def to_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "country": self.country,
            "city": self.city,
            "coords": self.coords,
            "tier": self.tier,
            "status": self.status,
            "activation_week": self.activation_week,
            "enrolled_count": self.enrolled_count,
            "protocol_deviations": self.protocol_deviations,
            "performance_score": round(self.performance_score, 3),
            "recruitment_rate": round(self.recruitment_rate, 2),
            "screen_failure_rate": round(self.screen_failure_rate, 3),
        }


class SiteManager:
    def __init__(self, n_sites: int = 8, rng: random.Random | None = None):
        self._rng = rng or random.Random(42)
        pool = self._rng.sample(SITE_POOL, min(n_sites, len(SITE_POOL)))
        self.sites: List[ClinicalSite] = [
            ClinicalSite(
                site_id=f"SITE-{str(i+1).zfill(3)}",
                country=s["country"], city=s["city"],
                coords=s["coords"], tier=s["tier"],
            )
            for i, s in enumerate(pool)
        ]
        self._activation_schedule: dict[int, int] = {}  # week → n_sites to activate

    def schedule_activations(self, total_weeks: int) -> None:
        """Stagger site activations over the first third of the trial."""
        n = len(self.sites)
        window = max(1, total_weeks // 3)
        per_wave = max(1, n // 3)
        for i, site in enumerate(self.sites):
            wave = i // per_wave
            site_week = wave * (window // 3) + self._rng.randint(0, 2)
            self._activation_schedule[site.site_id] = site_week

    def step(self, week: int) -> tuple[int, List[dict]]:
        """Advance all sites one week. Returns (new_patients_total, site_snapshots)."""
        # Activate newly scheduled sites
        for site in self.sites:
            if site.status == "pending" and self._activation_schedule.get(site.site_id, 9999) <= week:
                site.activate(week, self._rng)

        total_new = 0
        for site in self.sites:
            total_new += site.step(week, self._rng)

        return total_new, [s.to_dict() for s in self.sites]

    def snapshot(self) -> List[dict]:
        return [s.to_dict() for s in self.sites]
