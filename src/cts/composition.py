from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompositionComponent:
    name: str
    mechanism: str
    toxicity_weight: float
    efficacy_weight: float
    target_pathway: str = ""
    chembl_id: str = ""


def constrained_composition_update(
    current: dict[str, float],
    delta: dict[str, float],
    max_weekly_jump: float = 0.15,
    max_toxicity_score: float = 0.7,
    min_efficacy_score: float = 0.2,
    component_metadata: dict[str, CompositionComponent] | None = None,
) -> dict[str, float]:
    updated = dict(current)
    for key, value in delta.items():
        prev = updated.get(key, 0.0)
        clipped = max(prev - max_weekly_jump, min(prev + max_weekly_jump, prev + value))
        updated[key] = max(0.0, min(1.0, clipped))
    
    # Ensure all components exist in updated
    if component_metadata:
        for k in component_metadata:
            if k not in updated:
                updated[k] = 0.0
                
    total = sum(updated.values())
    if total < 1e-9:
        # Fallback to equal distribution if all are zero
        keys = list(updated.keys()) or ["a", "b", "c"]
        updated = {k: 1.0 / len(keys) for k in keys}
    else:
        updated = {k: v / total for k, v in updated.items()}
    
    # Safety constraint check
    if component_metadata:
        tox_score = sum(updated[k] * component_metadata[k].toxicity_weight for k in updated if k in component_metadata)
        if tox_score > max_toxicity_score:
            # Reduce components with high toxicity weight
            toxic_components = sorted(
                [k for k in updated if k in component_metadata],
                key=lambda x: component_metadata[x].toxicity_weight,
                reverse=True
            )
            for k in toxic_components:
                if updated[k] > 0.05:
                    updated[k] -= 0.05
                    break
            # Renormalize
            t = sum(updated.values())
            updated = {k: v / t for k, v in updated.items()}
            
    return updated

