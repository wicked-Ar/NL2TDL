"""Pluggable LLM clients for requirement analysis.

Supports:
- Ollama (local) – tested with Gemma models (e.g., "gemma:2b", "gemma2:2b")
- Hugging Face Transformers (optional) – e.g., "google/gemma-2b-it" via text-generation pipeline

Usage is typically indirect via `get_llm_from_env()` and passing into
`analyze_requirement(requirement, llm=...)`.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .models import RequirementAnalysisResult


ANALYSIS_JSON_INSTRUCTIONS = (
    "You are a planner. Convert the user's instruction into a strict JSON object "
    "with keys: source_requirement (string), detected_actions (array of strings), "
    "objects (array of strings), source_location (string|null), target_location (string|null), "
    "constraints (object with numeric fields e.g., payload_kg, reach_m). "
    "Only output JSON, no extra text."
)


def _extract_first_json_block(text: str) -> str:
    """Extract the first top-level JSON object from text.

    This is robust against models adding prose around the JSON.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start found in model output")
    # naive stack-based matching
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unbalanced JSON braces in model output")


def _coerce_analysis_dict(payload: Dict[str, Any]) -> RequirementAnalysisResult:
    src = str(payload.get("source_requirement", ""))
    actions = [str(a) for a in (payload.get("detected_actions") or [])]
    objects = [str(o) for o in (payload.get("objects") or [])]
    source_location = payload.get("source_location")
    target_location = payload.get("target_location")
    source_location = None if source_location in ("", None) else str(source_location)
    target_location = None if target_location in ("", None) else str(target_location)

    constraints_obj = payload.get("constraints") or {}
    constraints: Dict[str, float] = {}
    for k, v in constraints_obj.items():
        try:
            constraints[str(k)] = float(v)
        except Exception:
            # ignore non-numeric
            continue

    return RequirementAnalysisResult(
        source_requirement=src,
        detected_actions=actions or ["analyze"],
        objects=objects,
        source_location=source_location,
        target_location=target_location,
        constraints=constraints,
    )


@dataclass
class BaseLLM:
    """Abstract base for LLM providers."""

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        raise NotImplementedError


@dataclass
class OllamaLLM(BaseLLM):
    model: str = "gemma:2b"
    endpoint: str = "http://localhost:11434"
    # use /api/generate to keep things simple and avoid chat formatting

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        prompt = (
            f"{ANALYSIS_JSON_INSTRUCTIONS}\n\n"
            f"User Instruction: {requirement}\n"
        )
        url = self.endpoint.rstrip("/") + "/api/generate"
        body = {"model": self.model, "prompt": prompt, "stream": False}

        # Prefer stdlib to avoid hard dependency on requests
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        output = data.get("response") or data.get("output") or ""
        json_text = _extract_first_json_block(output)
        analysis_payload = json.loads(json_text)
        return _coerce_analysis_dict(analysis_payload)


@dataclass
class HuggingFaceLLM(BaseLLM):
    model: str = "google/gemma-2b-it"
    device: Optional[str] = None  # e.g., "cuda:0" or "cpu"

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        try:
            from transformers import pipeline  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "transformers is required for HuggingFaceLLM. Install with `pip install transformers`"
            ) from e

        generator = pipeline(
            task="text-generation",
            model=self.model,
            device=self.device if self.device is not None else -1,
            max_new_tokens=512,
            do_sample=False,
        )

        prompt = (
            f"{ANALYSIS_JSON_INSTRUCTIONS}\n\n"
            f"User Instruction: {requirement}\n"
        )
        outputs = generator(prompt)
        text = outputs[0]["generated_text"] if outputs else ""
        json_text = _extract_first_json_block(text)
        analysis_payload = json.loads(json_text)
        return _coerce_analysis_dict(analysis_payload)


def get_llm_from_env() -> BaseLLM | None:
    provider = os.getenv("NL2TDL_LLM_PROVIDER", "").strip().lower()
    if not provider:
        return None

    if provider == "ollama":
        model = os.getenv("NL2TDL_LLM_MODEL", "gemma:2b")
        endpoint = os.getenv("NL2TDL_LLM_ENDPOINT", "http://localhost:11434")
        return OllamaLLM(model=model, endpoint=endpoint)

    if provider in ("hf", "huggingface"):
        model = os.getenv("NL2TDL_LLM_MODEL", "google/gemma-2b-it")
        device = os.getenv("NL2TDL_LLM_DEVICE")
        return HuggingFaceLLM(model=model, device=device)

    # Unknown provider -> disabled
    return None
