"""TDL document generator that converts structured analysis into task descriptions."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List

from .llm_client import BaseLLM
from .models import (
    CommandDefinition,
    GoalNode,
    RequirementAnalysisResult,
    TDLDocument,
    TDLHeader,
)
from .prompting import (
    create_analysis_prompt,
    create_architecture_extraction_prompt,
    create_synthesis_prompt,
)
from .rag import get_parsing_instructions, get_tdl_syntax_reference


COMMAND_LIBRARY: Dict[str, CommandDefinition] = {
    "SetJointVelocity": CommandDefinition(
        name="SetJointVelocity",
        signature="(velocity)",
        body="motion.configure_joint_velocity(velocity);",
    ),
    "MoveLinear": CommandDefinition(
        name="MoveLinear",
        signature="(pose, velocity, acceleration, tool, blend)",
        body=(
            "motion.execute(type=\"Linear\", pose=pose, vel=velocity, acc=acceleration, "
            "tool=tool, blend=blend);"
        ),
    ),
    "WaitForDigitalInput": CommandDefinition(
        name="WaitForDigitalInput",
        signature="(signal, state, timeout)",
        body="io.wait_for_digital(signal=signal, state=state, timeout=timeout);",
    ),
    "ReleaseCompliance": CommandDefinition(
        name="ReleaseCompliance",
        signature="()",
        body="compliance.release();",
    ),
    "SetTool": CommandDefinition(
        name="SetTool",
        signature="(tool_name)",
        body="tooling.activate(tool_name);",
    ),
    "GraspObject": CommandDefinition(
        name="GraspObject",
        signature="(force)",
        body="end_effector.grasp(force=force);",
    ),
    "ReleaseObject": CommandDefinition(
        name="ReleaseObject",
        signature="()",
        body="end_effector.release();",
    ),
}


def _build_source_job_text(analysis: RequirementAnalysisResult) -> str:
    """Render a pseudo job-file description for prompting purposes."""

    lines = ["# Natural language requirement", analysis.source_requirement.strip()]

    if analysis.detected_actions:
        lines.append("")
        lines.append("# Detected actions")
        for action in analysis.detected_actions:
            lines.append(f"action: {action}")

    if analysis.objects:
        lines.append("")
        lines.append("# Objects")
        for obj in analysis.objects:
            lines.append(f"object: {obj}")

    if analysis.source_location or analysis.target_location:
        lines.append("")
        lines.append("# Locations")
        if analysis.source_location:
            lines.append(f"source: {analysis.source_location}")
        if analysis.target_location:
            lines.append(f"target: {analysis.target_location}")

    if analysis.constraints:
        lines.append("")
        lines.append("# Constraints")
        for key, value in analysis.constraints.items():
            lines.append(f"{key}: {value}")

    if analysis.notes:
        lines.append("")
        lines.append("# Notes")
        for note in analysis.notes:
            lines.append(note)

    return "\n".join(lines).strip()


GOAL_PATTERN = re.compile(r"GOAL\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{(.*?)\}", re.DOTALL)
COMMENT_PATTERN = re.compile(r"//\s*(.*)")
SPAWN_PATTERN = re.compile(r"SPAWN\s+(.*)")


def _parse_goal_code(goal_code: str) -> List[GoalNode]:
    """Convert synthesized GOAL code into ``GoalNode`` objects."""

    goals: List[GoalNode] = []
    for match in GOAL_PATTERN.finditer(goal_code):
        name = match.group(1)
        block = match.group(2).strip()
        description = "Generated goal block"
        commands: List[str] = []

        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            comment_match = COMMENT_PATTERN.match(stripped)
            if comment_match and description == "Generated goal block":
                description = comment_match.group(1).strip() or description
                continue
            spawn_match = SPAWN_PATTERN.match(stripped)
            if spawn_match:
                commands.append(spawn_match.group(1).strip())

        goals.append(GoalNode(name=name, description=description, commands=commands))

    return goals


def _clean_command_definition_text(definition: str) -> str:
    """Remove wrapping keywords (COMMAND/DEFINE) from a definition string."""

    text = definition.strip()
    if text.startswith("COMMAND"):
        text = text[len("COMMAND") :].strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1].strip()
    if text.startswith("DEFINE"):
        text = text[len("DEFINE") :].strip()
    return text


COMMAND_DEF_PATTERN = re.compile(
    r"([A-Za-z0-9_]+)\s*(\([^)]*\))\s*\{(.*)\}\s*",
    re.DOTALL,
)


def _parse_command_definitions(
    definitions: Dict[str, str], used_signatures: List[str]
) -> List[CommandDefinition]:
    """Parse command definitions returned by the architecture agent."""

    results: List[CommandDefinition] = []
    seen: set[str] = set()
    for signature in used_signatures:
        definition_text = definitions.get(signature)
        if not definition_text or signature in seen:
            continue
        seen.add(signature)

        cleaned = _clean_command_definition_text(definition_text)
        match = COMMAND_DEF_PATTERN.match(cleaned)
        if not match:
            continue

        name = match.group(1)
        signature_text = match.group(2)
        body = match.group(3).strip()
        results.append(
            CommandDefinition(name=name, signature=signature_text, body=body)
        )

    return results


def _generate_tdl_document_with_llm(
    analysis: RequirementAnalysisResult,
    manufacturer: str,
    model: str,
    llm: BaseLLM,
) -> TDLDocument:
    """Run the multi-agent prompting pipeline to synthesize a TDL document."""

    parsing_instructions = get_parsing_instructions(manufacturer)
    if not parsing_instructions:
        raise ValueError("No parsing instructions available for prompting")

    source_job_file = _build_source_job_text(analysis)
    analysis_prompt = create_analysis_prompt(
        retrieved_instructions=parsing_instructions,
        source_job_file=source_job_file,
    )
    structured_logic_payload = json.loads(
        llm.generate_json(analysis_prompt, max_output_tokens=4096)
    )

    structured_logic_text = json.dumps(
        structured_logic_payload,
        ensure_ascii=False,
        indent=2,
    )

    tdl_syntax = get_tdl_syntax_reference(manufacturer)
    architecture_prompt = create_architecture_extraction_prompt(
        tdl_syntax_rules=tdl_syntax,
        structured_logic=structured_logic_text,
    )
    architecture_payload = json.loads(
        llm.generate_json(architecture_prompt, max_output_tokens=4096)
    )

    synthesis_prompt = create_synthesis_prompt(
        tdl_architecture=json.dumps(
            architecture_payload, ensure_ascii=False, indent=2
        ),
        structured_logic=structured_logic_text,
    )
    synthesis_payload = json.loads(
        llm.generate_json(synthesis_prompt, max_output_tokens=4096)
    )

    goal_code = synthesis_payload.get("goal_code", "")
    used_signatures = synthesis_payload.get("used_signatures", [])
    goals = _parse_goal_code(goal_code)

    command_definitions = _parse_command_definitions(
        architecture_payload.get("command_definitions", {}),
        used_signatures,
    )

    metadata = structured_logic_payload.get("logic", {}).get("metadata", {})
    converted_at_str = metadata.get("converted_at")
    converted_at = datetime.utcnow()
    if isinstance(converted_at_str, str):
        try:
            converted_at = datetime.fromisoformat(converted_at_str)
        except ValueError:
            pass

    header = TDLHeader(
        converted_at=converted_at,
        source_requirement=analysis.source_requirement,
        manufacturer=manufacturer,
        model=model,
    )

    if not goals or not command_definitions:
        raise ValueError("LLM synthesis returned incomplete TDL data")

    return TDLDocument(header=header, goals=goals, commands=command_definitions)


def _pick_command_names(actions: List[str]) -> List[str]:
    sequence: List[str] = []
    if "pick" in actions:
        sequence.extend(
            [
                "SetTool(\"gripper\")",
                "MoveLinear(PosX(0,0,0,0,0,0), 100, 50, \"gripper\", 0.0)",
                "GraspObject(40)",
            ]
        )
    if "move" in actions:
        sequence.append(
            "MoveLinear(PosX(100,200,300,0,0,0), 100, 50, \"gripper\", 0.1)"
        )
    if "place" in actions:
        sequence.extend(
            [
                "WaitForDigitalInput(11, ON, 10.0)",
                "ReleaseObject()",
            ]
        )
    return sequence


def _build_goals_heuristic(analysis: RequirementAnalysisResult) -> List[GoalNode]:
    initialize_commands = ["SetJointVelocity(30)", "SetTool(\"gripper\")"]
    execute_commands = _pick_command_names(analysis.detected_actions)
    execute_commands = [
        cmd for cmd in execute_commands if not cmd.startswith("ReleaseCompliance(")
    ]
    finalize_commands = ["ReleaseCompliance()"]

    description_suffix = (
        f" for {', '.join(analysis.objects)}" if analysis.objects else ""
    )

    return [
        GoalNode(
            name="Initialize_Process",
            description=f"Prepare robot configuration{description_suffix}",
            commands=initialize_commands,
        ),
        GoalNode(
            name="Execute_Process",
            description="Execute primary task sequence",
            commands=execute_commands,
        ),
        GoalNode(
            name="Finalize_Process",
            description="Return robot to safe state",
            commands=finalize_commands,
        ),
    ]


def _gather_commands_for_goals(goals: List[GoalNode]) -> List[CommandDefinition]:
    required_commands: Dict[str, CommandDefinition] = {}
    for goal in goals:
        for command_call in goal.commands:
            name = command_call.split("(")[0]
            if name in COMMAND_LIBRARY:
                required_commands[name] = COMMAND_LIBRARY[name]
    return list(required_commands.values())


def _generate_tdl_document_heuristic(
    analysis: RequirementAnalysisResult,
    manufacturer: str,
    model: str,
) -> TDLDocument:
    goals = _build_goals_heuristic(analysis)
    commands = _gather_commands_for_goals(goals)
    header = TDLHeader(
        converted_at=datetime.utcnow(),
        source_requirement=analysis.source_requirement,
        manufacturer=manufacturer,
        model=model,
    )
    return TDLDocument(header=header, goals=goals, commands=commands)


def generate_tdl_document(
    analysis: RequirementAnalysisResult,
    manufacturer: str,
    model: str,
    llm: BaseLLM | None = None,
) -> TDLDocument:
    """Generate a TDL document using the best available strategy."""

    if llm is not None:
        try:
            return _generate_tdl_document_with_llm(
                analysis=analysis,
                manufacturer=manufacturer,
                model=model,
                llm=llm,
            )
        except Exception as exc:  # pragma: no cover - fallback path
            analysis.notes.append(
                f"LLM-driven TDL synthesis failed; heuristic fallback used. ({exc})"
            )

    return _generate_tdl_document_heuristic(
        analysis=analysis,
        manufacturer=manufacturer,
        model=model,
    )
