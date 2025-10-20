"""Utilities for exporting generated TDL documents into vendor job files.

The exporter currently emits a textual job script inspired by Doosan's
DRL syntax. It performs a lightweight mapping from the high-level TDL
commands produced by this project into recognizable DRL primitives so
that integrators can take the output and refine it further inside their
robot programming environment.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Sequence

from .models import TDLDocument


def _split_comment(command_line: str) -> tuple[str, str | None]:
    """Separate inline ``//`` comments from a command string."""

    if "//" not in command_line:
        return command_line.strip(), None

    call, comment = command_line.split("//", 1)
    return call.strip(), comment.strip() or None


def _split_args(arg_text: str) -> List[str]:
    """Split a function argument string, preserving nested structures."""

    args: List[str] = []
    current: List[str] = []
    depth = 0
    in_string = False
    string_char = ""

    for char in arg_text:
        if in_string:
            current.append(char)
            if char == string_char:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            string_char = char
            current.append(char)
            continue

        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(depth - 1, 0)

        if char == "," and depth == 0:
            arg = "".join(current).strip()
            if arg:
                args.append(arg)
            current = []
            continue

        current.append(char)

    trailing = "".join(current).strip()
    if trailing:
        args.append(trailing)

    return args


def _format_time(value: datetime) -> str:
    """Format datetime for DRL-style headers."""

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _map_set_joint_velocity(args: Sequence[str]) -> str:
    velocity = args[0] if args else "0"
    return f"set_velj({velocity})"


def _map_move_linear(args: Sequence[str]) -> str:
    if len(args) < 5:
        return f"# Unsupported MoveLinear call: MoveLinear({', '.join(args)})"

    pose, velocity, acceleration, tool, blend = args[:5]
    tool_comment = f"  # tool={tool}" if tool else ""
    return f"movel({pose}, v={velocity}, a={acceleration}, radius={blend}){tool_comment}"


def _map_wait_for_digital_input(args: Sequence[str]) -> str:
    if not args:
        return "# Unsupported WaitForDigitalInput call: missing arguments"

    signal = args[0]
    state = args[1] if len(args) > 1 else "ON"
    timeout = args[2] if len(args) > 2 else "None"
    return f"wait_digital_input({signal}, {state}, timeout={timeout})"


def _map_release_compliance(_: Sequence[str]) -> str:
    return "release_compliance_ctrl()"


def _map_set_tool(args: Sequence[str]) -> str:
    tool = args[0] if args else '"default"'
    return f"set_tool({tool})"


def _map_grasp_object(args: Sequence[str]) -> str:
    force = args[0] if args else "0"
    return f"set_digital_output(1, ON)  # close gripper (force={force})"


def _map_release_object(_: Sequence[str]) -> str:
    return "set_digital_output(1, OFF)  # open gripper"


_COMMAND_MAPPERS = {
    "SetJointVelocity": _map_set_joint_velocity,
    "MoveLinear": _map_move_linear,
    "WaitForDigitalInput": _map_wait_for_digital_input,
    "ReleaseCompliance": _map_release_compliance,
    "SetTool": _map_set_tool,
    "GraspObject": _map_grasp_object,
    "ReleaseObject": _map_release_object,
}


def _convert_command(call: str) -> List[str]:
    """Convert a single TDL command invocation into job-file lines."""

    if not call:
        return []

    if "(" not in call or not call.endswith(")"):
        return [f"# Unsupported command syntax: {call}"]

    name, arg_text = call.split("(", 1)
    name = name.strip()
    arg_text = arg_text[:-1]  # drop trailing ')'

    mapper = _COMMAND_MAPPERS.get(name)
    args = _split_args(arg_text)

    if mapper is None:
        arg_display = f"({', '.join(args)})" if args else "()"
        return [f"# TODO: map {name}{arg_display} into a vendor job command"]

    return [mapper(args)]


def render_job_file(document: TDLDocument) -> str:
    """Render a vendor job-file approximation for the given TDL document."""

    header = document.header
    lines: List[str] = [
        f"Title : {header.model}_{header.manufacturer}_auto",
        f"Time : {_format_time(header.converted_at)}",
        f"# Source Requirement: {header.source_requirement}",
        f"# Manufacturer: {header.manufacturer}",
        f"# Model: {header.model}",
        "",
    ]

    for goal in document.goals:
        lines.append(f"# === GOAL {goal.name} ===")
        lines.append(f"# {goal.description}")
        for command in goal.commands:
            call, comment = _split_comment(command)
            converted_lines = _convert_command(call)
            if comment:
                lines.append(f"# {comment}")
            lines.extend(converted_lines)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
