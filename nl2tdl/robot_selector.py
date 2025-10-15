"""Robot constraint analysis for matching TDL requirements with robot capabilities."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .models import RobotCandidate, RobotSelectionResult, TDLDocument


@dataclass
class RobotSpec:
    manufacturer: str
    model: str
    payload_kg: float
    reach_m: float
    repeatability_mm: float
    energy_class: str

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "RobotSpec":
        return cls(
            manufacturer=str(data["manufacturer"]),
            model=str(data["model"]),
            payload_kg=float(data["payload_kg"]),
            reach_m=float(data["reach_m"]),
            repeatability_mm=float(data["repeatability_mm"]),
            energy_class=str(data.get("energy_class", "unknown")),
        )


@dataclass
class EvaluationCriteria:
    weight_payload: float = 0.4
    weight_reach: float = 0.3
    weight_repeatability: float = 0.2
    weight_energy: float = 0.1


ENERGY_SCORES = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "unknown": 0.5}


def load_robot_specs(path: Path) -> List[RobotSpec]:
    data = json.loads(path.read_text())
    return [RobotSpec.from_dict(item) for item in data]


def compute_score(robot: RobotSpec, criteria: EvaluationCriteria) -> float:
    normalized_payload = robot.payload_kg / 20.0
    normalized_reach = robot.reach_m / 2.0
    normalized_repeatability = max(0.0, 1.0 - robot.repeatability_mm / 0.1)
    energy_score = ENERGY_SCORES.get(robot.energy_class, ENERGY_SCORES["unknown"])

    return (
        normalized_payload * criteria.weight_payload
        + normalized_reach * criteria.weight_reach
        + normalized_repeatability * criteria.weight_repeatability
        + energy_score * criteria.weight_energy
    )


def passes_constraints(robot: RobotSpec, constraints: Dict[str, float]) -> bool:
    payload_requirement = constraints.get("payload_kg")
    reach_requirement = constraints.get("reach_m")

    if payload_requirement is not None and robot.payload_kg < payload_requirement:
        return False
    if reach_requirement is not None and robot.reach_m < reach_requirement:
        return False
    return True


def evaluate_robots(
    document: TDLDocument,
    robot_specs: Iterable[RobotSpec],
    criteria: EvaluationCriteria,
    constraints: Dict[str, float],
) -> RobotSelectionResult:
    candidates: List[RobotCandidate] = []
    validation_notes: List[str] = []

    execute_goal_commands = document.goals[1].commands if len(document.goals) > 1 else []
    if not any("Move" in command for command in execute_goal_commands):
        validation_notes.append("Execute goal does not contain an explicit movement command.")

    for spec in robot_specs:
        compliant = passes_constraints(spec, constraints)
        score = compute_score(spec, criteria) if compliant else 0.0
        candidates.append(
            RobotCandidate(
                manufacturer=spec.manufacturer,
                model=spec.model,
                payload=spec.payload_kg,
                reach=spec.reach_m,
                repeatability=spec.repeatability_mm,
                energy_class=spec.energy_class,
                score=round(score, 3),
                passes_constraints=compliant,
            )
        )

    verification_notes = []
    if not any(candidate.passes_constraints for candidate in candidates):
        verification_notes.append("No robot satisfies the mandatory constraints.")
    else:
        verification_notes.append("At least one robot satisfies payload and reach requirements.")

    candidates.sort(key=lambda c: c.score, reverse=True)

    return RobotSelectionResult(
        candidates=candidates,
        validation_notes=validation_notes,
        verification_notes=verification_notes,
    )
