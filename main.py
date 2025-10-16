"""CLI entry point for NL→TDL workflow with optional LLM integration.

This CLI accepts a requirement at runtime (argument, file, stdin, or prompt),
optionally configures an LLM provider, and prints the generated TDL and
supporting analysis.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from nl2tdl.robot_selector import EvaluationCriteria
from nl2tdl.llm_client import (
    get_llm_from_env,
)
from nl2tdl.workflow import NL2TDLWorkflow


def _read_requirement_from_inputs(
    arg_text: Optional[str], file_path: Optional[Path]
) -> str:
    if arg_text:
        return arg_text
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    # Interactive prompt as a last resort
    return input("Enter requirement: ").strip()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a natural language requirement to a TDL document. "
            "Optionally use an LLM for analysis (env or flags)."
        )
    )

    # Input
    parser.add_argument(
        "-r",
        "--requirement",
        type=str,
        help="Requirement text (if omitted, read from --file, stdin, or prompt)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Path to a text file containing the requirement",
    )

    # Robot/TDL config
    parser.add_argument(
        "--manufacturer",
        default="doosan",
        help="Robot manufacturer metadata for generated TDL header",
    )
    parser.add_argument(
        "--model-name",
        default="h2017",
        help="Robot model metadata for generated TDL header",
    )
    parser.add_argument(
        "--robot-db",
        type=Path,
        default=Path("robots_db.json"),
        help="Path to robot specs JSON database",
    )

    # Output controls
    parser.add_argument(
        "--tdl-only",
        action="store_true",
        help="Print only the TDL text (suppress other sections)",
    )
    parser.add_argument(
        "--write-tdl",
        type=Path,
        help="Optional path to write the TDL text output",
    )

    # LLM selection (env remains the default)
    parser.add_argument(
        "--provider",
        choices=["ollama", "hf", "none"],
        help=(
            "LLM provider override. If omitted, uses environment (NL2TDL_LLM_PROVIDER) or heuristic fallback."
        ),
    )
    parser.add_argument(
        "--llm-model",
        help="Model identifier for the selected provider (e.g., gemma:2b or google/gemma-2b-it)",
    )
    parser.add_argument(
        "--llm-endpoint",
        help="Ollama endpoint (e.g., http://localhost:11434)",
    )
    parser.add_argument(
        "--llm-device",
        help="HuggingFace device string (e.g., cuda:0 or cpu)",
    )

    return parser


def resolve_llm_from_args(namespace: argparse.Namespace):
    """Return a BaseLLM instance or None based on CLI args/env.

    - If --provider is 'none', returns None (heuristic mode)
    - If --provider is omitted, use get_llm_from_env()
    - If --provider is set to 'ollama' or 'hf', use env defaults where args are missing
    """
    provider = getattr(namespace, "provider", None)
    if provider == "none":
        return None
    if provider is None:
        return get_llm_from_env()

    # Late import to avoid unnecessary dependencies at startup
    from nl2tdl.llm_client import OllamaLLM, HuggingFaceLLM

    if provider == "ollama":
        model = namespace.llm_model or "gemma:2b"
        endpoint = namespace.llm_endpoint or "http://localhost:11434"
        return OllamaLLM(model=model, endpoint=endpoint)

    if provider == "hf":
        model = namespace.llm_model or "google/gemma-2b-it"
        device = namespace.llm_device
        return HuggingFaceLLM(model=model, device=device)

    return None


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    requirement = _read_requirement_from_inputs(args.requirement, args.file)
    llm = resolve_llm_from_args(args)

    workflow = NL2TDLWorkflow(
        manufacturer=args.manufacturer,
        model=args.model_name,
        robot_database=Path(args.robot_db),
        evaluation_criteria=EvaluationCriteria(),
        llm=llm,
    )

    result = workflow.run(requirement)

    # Output handling
    if args.tdl_only:
        tdl_text = result.tdl_document.to_text()
        print(tdl_text)
        if args.write_tdl:
            Path(args.write_tdl).write_text(tdl_text, encoding="utf-8")
        return

    print("=== Requirement Analysis ===")
    print(result.requirement_analysis)
    print("\n=== Generated TDL ===")
    tdl_text = result.tdl_document.to_text()
    print(tdl_text)
    if args.write_tdl:
        Path(args.write_tdl).write_text(tdl_text, encoding="utf-8")
    print("\n=== Validation Report ===")
    print(result.validation_report)
    print("\n=== Verification Report ===")
    print(result.verification_report)
    print("\n=== Robot Selection ===")
    for candidate in result.robot_selection.candidates:
        status = "PASS" if candidate.passes_constraints else "FAIL"
        print(f"{candidate.manufacturer} {candidate.model}: {status} score={candidate.score}")
    print("Validation Notes:", result.robot_selection.validation_notes)
    print("Verification Notes:", result.robot_selection.verification_notes)


if __name__ == "__main__":
    main()
