"""TDL document generator that converts structured analysis into task descriptions."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from .models import CommandDefinition, GoalNode, RequirementAnalysisResult, TDLDocument, TDLHeader

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


def pick_command_names(actions: List[str]) -> List[str]:
    sequence: List[str] = []
    if "pick" in actions:
        sequence.extend([
            "SetTool(\"gripper\")",
            "MoveLinear(PosX(0,0,0,0,0,0), 100, 50, \"gripper\", 0.0)",
            "GraspObject(40)",
        ])
    if "move" in actions:
        sequence.append("MoveLinear(PosX(100,200,300,0,0,0), 100, 50, \"gripper\", 0.1)")
    if "place" in actions:
        sequence.extend([
            "WaitForDigitalInput(11, ON, 10.0)",
            "ReleaseObject()",
        ])
    return sequence


def build_goals(analysis: RequirementAnalysisResult) -> List[GoalNode]:
    initialize_commands = ["SetJointVelocity(30)", "SetTool(\"gripper\")"]
    execute_commands = pick_command_names(analysis.detected_actions)
    # Ensure ReleaseCompliance appears only once, in Finalize
    execute_commands = [c for c in execute_commands if not c.startswith("ReleaseCompliance(")]
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


def gather_commands(goals: List[GoalNode]) -> List[CommandDefinition]:
    required_commands: Dict[str, CommandDefinition] = {}
    for goal in goals:
        for command_call in goal.commands:
            name = command_call.split("(")[0]
            if name in COMMAND_LIBRARY:
                required_commands[name] = COMMAND_LIBRARY[name]
    return list(required_commands.values())


def generate_tdl_document(
    analysis: RequirementAnalysisResult,
    manufacturer: str,
    model: str,
) -> TDLDocument:
    goals = build_goals(analysis)
    commands = gather_commands(goals)
    header = TDLHeader(
        converted_at=datetime.utcnow(),
        source_requirement=analysis.source_requirement,
        manufacturer=manufacturer,
        model=model,
    )
    return TDLDocument(header=header, goals=goals, commands=commands)
