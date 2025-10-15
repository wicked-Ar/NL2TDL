"""Core datamodels representing the NL to TDL workflow artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RequirementAnalysisResult:
    """Structured information extracted from the natural language requirement."""

    source_requirement: str
    detected_actions: List[str]
    objects: List[str]
    source_location: Optional[str]
    target_location: Optional[str]
    constraints: Dict[str, float]
    notes: List[str] = field(default_factory=list)


@dataclass
class GoalNode:
    """Representation of a GOAL block entry."""

    name: str
    description: str
    commands: List[str]


@dataclass
class CommandDefinition:
    """Low level command definition used in the COMMAND block."""

    name: str
    signature: str
    body: str


@dataclass
class TDLHeader:
    """Metadata describing the generated TDL document."""

    converted_at: datetime
    source_requirement: str
    manufacturer: str
    model: str


@dataclass
class TDLDocument:
    """Full TDL document, composed of header, goals and commands."""

    header: TDLHeader
    goals: List[GoalNode]
    commands: List[CommandDefinition]

    def to_text(self) -> str:
        """Render the TDL document to a textual representation."""

        header_block = (
            "HEADER {\n"
            f"    Converted At: {self.header.converted_at.isoformat()}\n"
            f"    Source Requirement: \"{self.header.source_requirement}\"\n"
            f"    Manufacturer: {self.header.manufacturer}\n"
            f"    Model: {self.header.model}\n"
            "}\n\n"
        )

        goal_blocks = []
        for goal in self.goals:
            commands = "\n".join(f"    SPAWN {cmd}" for cmd in goal.commands)
            goal_blocks.append(
                f"GOAL {goal.name}() {{\n"
                f"    // {goal.description}\n"
                f"{commands}\n"
                "}\n"
            )
        goals_text = "\n".join(goal_blocks)

        command_blocks = []
        for cmd in self.commands:
            command_blocks.append(
                "COMMAND {\n"
                f"    DEFINE {cmd.name}{cmd.signature} {{\n"
                f"        {cmd.body}\n"
                "    }\n"
                "}\n"
            )
        commands_text = "\n".join(command_blocks)

        return f"{header_block}{goals_text}\n\n{commands_text}".strip()


@dataclass
class ValidationReport:
    """Human facing validation messages used to confirm correctness."""

    summary: str
    confirm_prompt: str
    issues: List[str]


@dataclass
class VerificationReport:
    """Machine level verification output."""

    syntax_ok: bool
    schema_ok: bool
    logical_ok: bool
    details: List[str]


@dataclass
class RobotCandidate:
    """Candidate robot evaluation information."""

    manufacturer: str
    model: str
    payload: float
    reach: float
    repeatability: float
    energy_class: str
    score: float
    passes_constraints: bool


@dataclass
class RobotSelectionResult:
    """Result of the robot constraint analysis stage."""

    candidates: List[RobotCandidate]
    validation_notes: List[str]
    verification_notes: List[str]
