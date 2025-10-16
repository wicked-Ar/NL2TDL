"""Example CLI entry point for the NL to TDL workflow prototype."""
from __future__ import annotations

from pathlib import Path

from nl2tdl.robot_selector import EvaluationCriteria
from nl2tdl.llm_client import get_llm_from_env
from nl2tdl.workflow import NL2TDLWorkflow


def main() -> None:
    requirement = (
        "Move the component from stationA to stationB avoiding obstacles while carrying a 5 kg payload."
    )
    workflow = NL2TDLWorkflow(
        manufacturer="doosan",
        model="h2017",
        robot_database=Path("robots_db.json"),
        evaluation_criteria=EvaluationCriteria(),
        llm=get_llm_from_env(),
    )

    result = workflow.run(requirement)

    print("=== Requirement Analysis ===")
    print(result.requirement_analysis)
    print("\n=== Generated TDL ===")
    print(result.tdl_document.to_text())
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
