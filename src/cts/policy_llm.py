from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from cts.config import TrialConfig
from cts.environment.models import Action, ActionType, TrialState


def _state_to_prompt(state: TrialState, agent_outputs: dict[str, Any] | None = None, evidence: list[str] | None = None) -> str:
    prompt = (
        "You are the Chief Trial Scientist for a simulated research clinical trial. "
        "Analyze the provided state, agent insights, and evidence to decide the next action. "
        "Return JSON only with the following schema:\n"
        "{\n"
        "  \"action_type\": \"recruit|adjust_dose|update_composition|hold_enrollment|file_interim_report|noop\",\n"
        "  \"magnitude\": float,\n"
        "  \"composition\": {\"a\": float, \"b\": float, \"c\": float},\n"
        "  \"rationale\": \"string\",\n"
        "  \"evidence_ids\": [\"string\"],\n"
        "  \"patient_impact_summary\": \"string\",\n"
        "  \"safety_controls\": [\"string\"]\n"
        "}\n\n"
        "IMPORTANT: This is for research simulation only. Not medical advice. No real PHI involved.\n\n"
        f"State: week={state.week}, stage={state.stage_name}, enrolled={state.enrolled}, active={state.active}, "
        f"completed={state.completed}, adverse_events={state.adverse_events}, "
        f"serious_adverse_events={state.serious_adverse_events}, budget_spent={state.budget_spent:.2f}, "
        f"dose_level={state.dose_level:.3f}, efficacy_signal={state.efficacy_signal:.3f}, "
        f"biomarker_improvement={state.biomarker_improvement:.3f}, recruitment_hold={int(state.recruitment_hold)}, "
        f"composition={state.composition}.\n"
    )
    if agent_outputs:
        prompt += f"\nAgent Insights: {json.dumps(agent_outputs)}\n"
    if evidence:
        prompt += f"\nEvidence Snippets: {json.dumps(evidence)}\n"
    
    return prompt


def parse_llm_action_text(text: str) -> dict[str, Any]:
    body = text.strip()
    if body.startswith("```"):
        body = body.strip("`").strip()
    if body.startswith("json"):
        body = body[4:].strip()

    action_raw = "noop"
    magnitude = 0.0
    composition = {}
    valid_json = False
    candidate = None
    
    try:
        candidate = json.loads(body)
        valid_json = isinstance(candidate, dict)
    except Exception:
        try:
            # Try to find a JSON-like block if it's buried in text
            match = re.search(r"\{.*\}", body, re.DOTALL)
            if match:
                candidate = json.loads(match.group(0))
                valid_json = True
        except Exception:
            candidate = None

    if isinstance(candidate, dict):
        action_raw = str(candidate.get("action_type", "noop")).strip().lower()
        mag_val = candidate.get("magnitude", 0.0)
        try:
            magnitude = float(mag_val)
        except (ValueError, TypeError):
            # Fallback for semantic strings like "diminish", "small", etc.
            magnitude = 0.1 if str(mag_val).lower() in ["small", "diminish", "slight"] else 0.0
        composition = candidate.get("composition", {})
    
    valid_action = True
    try:
        action_type = ActionType(action_raw)
    except ValueError:
        action_type = ActionType.NOOP
        valid_action = False

    return {
        "action_type": action_type,
        "magnitude": magnitude,
        "composition": composition,
        "rationale": candidate.get("rationale", "") if candidate else "",
        "evidence_ids": candidate.get("evidence_ids", []) if candidate else [],
        "patient_impact": candidate.get("patient_impact_summary", "") if candidate else "",
        "valid_json": valid_json,
        "valid_action": valid_action,
    }


def _parse_action_payload(text: str) -> tuple[ActionType, float]:
    parsed = parse_llm_action_text(text)
    return parsed["action_type"], float(parsed["magnitude"])


class LLMPolicy:
    """Model-backed policy adapter that maps trial state text to discrete actions."""

    def __init__(
        self,
        model_dir: str,
        model_name: str,
        max_new_tokens: int = 64,
        adapter_dir: str | None = None,
    ):
        self.model_dir = model_dir
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.adapter_dir = adapter_dir

        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

        # Prefer loading tokenizer/base model from the declared base model name.
        # model_dir is retained for backward-compatible checkpoints that only store local artifacts.
        source = model_name or model_dir
        if not source:
            raise ValueError("LLMPolicy requires model_name or model_dir")

        self.tokenizer = AutoTokenizer.from_pretrained(source)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(source)
        if adapter_dir and Path(adapter_dir).exists():
            from peft import PeftModel  # type: ignore

            model = PeftModel.from_pretrained(model, adapter_dir)
        elif model_dir and Path(model_dir).exists() and model_dir != source:
            model = AutoModelForCausalLM.from_pretrained(model_dir)
        self.model = model
        self.model.eval()

    def select_action(
        self,
        state: TrialState,
        config: TrialConfig,
        rng,
        stochastic: bool = False,
        agent_outputs: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
    ) -> Action:
        del config, rng, stochastic
        prompt = _state_to_prompt(state, agent_outputs=agent_outputs, evidence=evidence)
        encoded = self.tokenizer(prompt, return_tensors="pt")
        output = self.model.generate(
            **encoded,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        generated = self.tokenizer.decode(output[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True)
        parsed = parse_llm_action_text(generated)
        return Action(
            type=parsed["action_type"],
            magnitude=parsed["magnitude"],
            composition=parsed["composition"],
        )


def save_llm_policy_checkpoint(
    path: str,
    model_dir: str,
    model_name: str,
    metadata: dict | None = None,
    adapter_dir: str | None = None,
) -> None:
    payload = {
        "format_version": 1,
        "policy_type": "llm_causal",
        "model_dir": model_dir,
        "model_name": model_name,
        "adapter_dir": adapter_dir or "",
        "metadata": metadata or {},
    }
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_llm_policy_checkpoint(path: str) -> LLMPolicy:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("policy_type") != "llm_causal":
        raise ValueError("Unsupported checkpoint policy type for LLM policy")
    return LLMPolicy(
        model_dir=str(payload.get("model_dir", "")),
        model_name=str(payload.get("model_name", "")),
        max_new_tokens=int(payload.get("metadata", {}).get("max_new_tokens", 64)),
        adapter_dir=str(payload.get("adapter_dir", "")).strip() or None,
    )
