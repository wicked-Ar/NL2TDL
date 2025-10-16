"""High level orchestration for the NL to TDL workflow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .models import (
    RequirementAnalysisResult,
    RobotSelectionResult,
    TDLDocument,
    ValidationReport,
    VerificationReport,
)
from .requirement_analysis import analyze_requirement
from .robot_selector import EvaluationCriteria, evaluate_robots, load_robot_specs
from .tdl_generator import generate_tdl_document
from .validators import build_validation_report, verify_tdl
from .llm_client import get_llm_from_env, BaseLLM


@dataclass
class WorkflowResult:
    requirement_analysis: RequirementAnalysisResult
    tdl_document: TDLDocument
    validation_report: ValidationReport
    verification_report: VerificationReport
    robot_selection: RobotSelectionResult


class NL2TDLWorkflow:
    """Runs the user requirement to robot selection pipeline."""

    def __init__(
        self,
        manufacturer: str,
        model: str,
        robot_database: Path,
        evaluation_criteria: EvaluationCriteria | None = None,
        llm: BaseLLM | None = None,
    ) -> None:
        self.manufacturer = manufacturer
        self.model = model
        self.robot_database = robot_database
        self.evaluation_criteria = evaluation_criteria or EvaluationCriteria()
        # If not explicitly provided, attempt to resolve from env
        self.llm = llm if llm is not None else get_llm_from_env()

    def run(self, requirement: str) -> WorkflowResult:
        analysis = analyze_requirement(requirement, llm=self.llm)

        tdl_document = generate_tdl_document(
            analysis=analysis,
            manufacturer=self.manufacturer,
            model=self.model,
        )

        validation_report = build_validation_report(tdl_document)
        verification_report = verify_tdl(tdl_document)

        robot_specs = load_robot_specs(self.robot_database)
        robot_selection = evaluate_robots(
            document=tdl_document,
            robot_specs=robot_specs,
            criteria=self.evaluation_criteria,
            constraints=analysis.constraints,
        )

        return WorkflowResult(
            requirement_analysis=analysis,
            tdl_document=tdl_document,
            validation_report=validation_report,
            verification_report=verification_report,
            robot_selection=robot_selection,
        )
