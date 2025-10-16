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

## Optional: LLM Integration (Gemma via Ollama or Hugging Face)

You can enable LLM-assisted requirement analysis to improve parsing quality.

- Ollama (local, recommended for Gemma):
  1. Install Ollama and pull a Gemma model (e.g., `gemma:2b`).
  2. Set environment variables before running:
     ```bash
     export NL2TDL_LLM_PROVIDER=ollama
     export NL2TDL_LLM_MODEL=gemma:2b
     export NL2TDL_LLM_ENDPOINT=http://localhost:11434
     python main.py
     ```

- Hugging Face Transformers:
  1. Install dependencies:
     ```bash
     pip install transformers accelerate torch --extra-index-url https://download.pytorch.org/whl/cpu
     ```
  2. Set environment variables:
     ```bash
     export NL2TDL_LLM_PROVIDER=hf
     export NL2TDL_LLM_MODEL=google/gemma-2b-it
     # optional: NL2TDL_LLM_DEVICE=cuda:0
     python main.py
     ```

Behavior:
- If environment variables are not set or the model call fails, the system falls back to the built-in heuristic parser.
- The LLM is prompted to output a strict JSON with fields accepted by the pipeline (actions, objects, locations, constraints like `payload_kg`, `reach_m`).
