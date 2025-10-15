"""Validation and verification utilities for the NL to TDL workflow."""
from __future__ import annotations

import re
from typing import List

from .models import TDLDocument, ValidationReport, VerificationReport

GOAL_PATTERN = re.compile(r"GOAL\s+([A-Za-z0-9_]+)\(\)\s*{", re.MULTILINE)
COMMAND_PATTERN = re.compile(r"COMMAND\s*{\s*DEFINE\s+([A-Za-z0-9_]+)\(", re.MULTILINE)


VALIDATION_TEMPLATE = (
    "The generated TDL decomposes the task into the following high-level steps: {steps}. "
    "Please confirm that the robot should act this way."
)

CONFIRM_PROMPT = "로봇이 위와 같이 동작하는 것이 맞습니까? (예/아니오)"


def build_validation_report(document: TDLDocument) -> ValidationReport:
    goal_names = [goal.name.replace("_", " ") for goal in document.goals]
    summary = VALIDATION_TEMPLATE.format(steps=", ".join(goal_names))
    issues: List[str] = []
    if not any("Execute" in goal.name for goal in document.goals):
        issues.append("No Execute goal found; confirm task breakdown.")
    return ValidationReport(summary=summary, confirm_prompt=CONFIRM_PROMPT, issues=issues)


def verify_tdl(document: TDLDocument) -> VerificationReport:
    tdl_text = document.to_text()
    syntax_ok = bool(GOAL_PATTERN.search(tdl_text)) and bool(COMMAND_PATTERN.search(tdl_text))

    schema_ok = len(document.goals) >= 3 and len(document.commands) > 0

    logical_details: List[str] = []
    logical_ok = True
    for goal in document.goals:
        if not goal.commands:
            logical_details.append(f"Goal {goal.name} has no commands")
            logical_ok = False
        if goal.name.startswith("Execute") and all("Move" not in cmd for cmd in goal.commands):
            logical_details.append(
                f"Execute goal {goal.name} does not contain any movement commands"
            )
            logical_ok = False

    if not logical_details:
        logical_details.append("TDL commands pass logical consistency checks.")

    return VerificationReport(
        syntax_ok=syntax_ok,
        schema_ok=schema_ok,
        logical_ok=logical_ok,
        details=logical_details,
    )
