"""Drug supply chain simulation — IMP management, cold chain, expiry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SupplyBatch:
    batch_id: str
    units: int
    ordered_week: int
    arrival_week: int   # 4-week lead time
    expiry_week: int    # 52 weeks shelf life
    units_remaining: int = 0

    def __post_init__(self):
        self.units_remaining = self.units


@dataclass
class DrugSupplyChain:
    lead_time_weeks: int = 4
    shelf_life_weeks: int = 52
    units_per_patient_per_week: int = 1
    # Inventory
    batches: List[SupplyBatch] = field(default_factory=list)
    _batch_counter: int = 0
    # Metrics
    total_ordered: int = 0
    total_dispensed: int = 0
    total_wasted: int = 0
    stockout_weeks: int = 0

    def order(self, units: int, current_week: int) -> SupplyBatch:
        self._batch_counter += 1
        batch = SupplyBatch(
            batch_id=f"BATCH-{self._batch_counter:04d}",
            units=units,
            ordered_week=current_week,
            arrival_week=current_week + self.lead_time_weeks,
            expiry_week=current_week + self.lead_time_weeks + self.shelf_life_weeks,
        )
        self.batches.append(batch)
        self.total_ordered += units
        return batch

    def available_units(self, current_week: int) -> int:
        return sum(
            b.units_remaining for b in self.batches
            if b.arrival_week <= current_week and b.expiry_week > current_week
        )

    def step(self, n_active_patients: int, current_week: int) -> dict:
        """Dispense drugs for active patients; expire old batches."""
        needed = n_active_patients * self.units_per_patient_per_week
        dispensed = 0
        # Dispense from oldest batches first (FEFO — first expired first out)
        valid_batches = sorted(
            [b for b in self.batches if b.arrival_week <= current_week and b.expiry_week > current_week],
            key=lambda b: b.expiry_week
        )
        for batch in valid_batches:
            take = min(batch.units_remaining, needed - dispensed)
            batch.units_remaining -= take
            dispensed += take
            if dispensed >= needed:
                break

        # Expire batches
        wasted_this_week = 0
        for batch in self.batches:
            if batch.expiry_week <= current_week and batch.units_remaining > 0:
                wasted_this_week += batch.units_remaining
                batch.units_remaining = 0

        self.total_dispensed += dispensed
        self.total_wasted += wasted_this_week
        stockout = dispensed < needed
        if stockout:
            self.stockout_weeks += 1

        return {
            "dispensed": dispensed,
            "needed": needed,
            "available_before": self.available_units(current_week) + dispensed,
            "stockout": stockout,
            "wasted_this_week": wasted_this_week,
            "total_ordered": self.total_ordered,
            "total_dispensed": self.total_dispensed,
            "total_wasted": self.total_wasted,
            "stockout_weeks": self.stockout_weeks,
        }

    def weeks_of_supply_remaining(self, n_active: int, current_week: int) -> float:
        avail = self.available_units(current_week)
        if n_active == 0:
            return float("inf")
        return avail / n_active

    def in_transit(self, current_week: int) -> int:
        return sum(b.units for b in self.batches if b.ordered_week <= current_week < b.arrival_week)

    def snapshot(self, current_week: int) -> dict:
        return {
            "available_units": self.available_units(current_week),
            "in_transit_units": self.in_transit(current_week),
            "total_ordered": self.total_ordered,
            "total_dispensed": self.total_dispensed,
            "total_wasted": self.total_wasted,
            "stockout_weeks": self.stockout_weeks,
            "weeks_of_supply": round(self.weeks_of_supply_remaining(1, current_week), 1),
            "batches": [
                {
                    "batch_id": b.batch_id,
                    "units_remaining": b.units_remaining,
                    "arrival_week": b.arrival_week,
                    "expiry_week": b.expiry_week,
                    "status": "available" if b.arrival_week <= current_week < b.expiry_week
                               else ("in_transit" if b.ordered_week <= current_week < b.arrival_week
                               else "expired"),
                }
                for b in self.batches
            ],
        }
