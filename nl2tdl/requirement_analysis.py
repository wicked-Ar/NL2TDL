"""Natural language requirement analysis that prepares inputs for TDL generation.

This module supports two analysis modes:
- Heuristic extraction (default, no external dependencies)
- LLM-assisted extraction (optional), when an `llm` client is provided
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import RequirementAnalysisResult
from .llm_client import BaseLLM

# Simple keyword dictionary for quick heuristics.
ACTION_KEYWORDS = {
    "pick": ["pick", "grasp", "grab", "collect", "lift"],
    "place": ["place", "put", "set", "drop"],
    "move": ["move", "transfer", "carry", "deliver"],
    "wait": ["wait", "hold"],
}

OBJECT_PATTERN = re.compile(r"(object|box|cup|component|part|tool|payload)", re.IGNORECASE)
LOCATION_PATTERN = re.compile(r"from ([\w-]+) to ([\w-]+)", re.IGNORECASE)
PAYLOAD_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)", re.IGNORECASE)
REACH_PATTERN = re.compile(r"reach(?:es)?\s*(\d+(?:\.\d+)?)\s*(?:mm|millimeters?|cm|centimeters?|m|meters?)",
                           re.IGNORECASE)


@dataclass
class RequirementMetadata:
    """Additional metadata derived from the requirement text."""

    required_payload: float | None
    required_reach: float | None


METRIC_CONVERSIONS: Dict[str, float] = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
}


def normalize_distance(value: float, unit: str) -> float:
    unit = unit.lower()
    base_unit = unit.rstrip('s')
    if base_unit not in METRIC_CONVERSIONS:
        return value
    return value * METRIC_CONVERSIONS[base_unit]


def detect_actions(requirement: str) -> List[str]:
    actions: List[str] = []
    lower_requirement = requirement.lower()
    for canonical, synonyms in ACTION_KEYWORDS.items():
        if any(keyword in lower_requirement for keyword in synonyms):
            actions.append(canonical)
    return actions or ["analyze"]


def detect_object_terms(requirement: str) -> List[str]:
    return list({match.group(0).lower() for match in OBJECT_PATTERN.finditer(requirement)})


def detect_locations(requirement: str) -> Tuple[str | None, str | None]:
    match = LOCATION_PATTERN.search(requirement)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def extract_payload(requirement: str) -> float | None:
    match = PAYLOAD_PATTERN.search(requirement)
    if match:
        return float(match.group(1))
    return None


def extract_reach(requirement: str) -> float | None:
    reach_match = REACH_PATTERN.search(requirement)
    if not reach_match:
        return None
    value = float(reach_match.group(1))
    unit_match = re.search(r"(mm|millimeters?|cm|centimeters?|m|meters?)", reach_match.group(0), re.IGNORECASE)
    if not unit_match:
        return value
    unit = unit_match.group(0)
    return normalize_distance(value, unit)


def analyze_requirement_heuristic(requirement: str) -> RequirementAnalysisResult:
    """Heuristic, dependency-free extraction for baseline analysis."""

    actions = detect_actions(requirement)
    objects = detect_object_terms(requirement)
    source_location, target_location = detect_locations(requirement)
    payload = extract_payload(requirement)
    reach = extract_reach(requirement)

    constraints: Dict[str, float] = {}
    if payload is not None:
        constraints["payload_kg"] = payload
    if reach is not None:
        constraints["reach_m"] = reach

    notes: List[str] = []
    if not objects:
        notes.append("No explicit object detected; default handling will be applied.")
    if source_location and target_location:
        notes.append(f"Detected transfer from {source_location} to {target_location}.")

    return RequirementAnalysisResult(
        source_requirement=requirement,
        detected_actions=actions,
        objects=objects,
        source_location=source_location,
        target_location=target_location,
        constraints=constraints,
        notes=notes,
    )


def analyze_requirement(requirement: str, llm: BaseLLM | None = None) -> RequirementAnalysisResult:
    """Produce a semantic analysis of the natural language requirement.

    When an LLM client is provided, attempt LLM-based parsing first.
    On error, fall back to heuristic extraction to ensure robustness.
    """
    if llm is not None:
        try:
            return llm.analyze_requirement(requirement)
        except Exception:
            # Fall back to heuristics if LLM fails for any reason
            result = analyze_requirement_heuristic(requirement)
            result.notes.append("LLM analysis failed; heuristic fallback applied.")
            return result

    return analyze_requirement_heuristic(requirement)
