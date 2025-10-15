# NL2TDL Prototype

This repository contains a lightweight prototype of the natural language to Task Description Language (TDL) workflow. It demonstrates the first three stages of the larger pipeline:

1. **User Requirement Analysis** – heuristic extraction of actions, objects, locations, and constraints from a natural language instruction.
2. **TDL Generation** – production of a TDL document with header metadata, Initialize/Execute/Finalize goal blocks, and required command definitions.
3. **Robot Constraint Analysis** – evaluation of candidate robots against the derived constraints with validation and verification support.

## Project Layout

- `nl2tdl/`
  - `models.py` – dataclasses that define the shared data structures for the workflow.
  - `requirement_analysis.py` – heuristics that convert natural language text into structured requirements.
  - `tdl_generator.py` – logic for building TDL documents from analyzed requirements.
  - `validators.py` – validation and verification routines, including schema checks.
  - `robot_selector.py` – robot capability assessment against payload/reach constraints.
  - `workflow.py` – orchestration that ties all stages together.
- `robots_db.json` – sample robot specifications used for selection.
- `main.py` – runnable example that executes the workflow end-to-end.

## Running the Example

```bash
python main.py
```

The script prints the analysis results, generated TDL, validation/verification feedback, and a ranked list of candidate robots.
