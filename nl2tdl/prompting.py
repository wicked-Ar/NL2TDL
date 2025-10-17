"""Prompt templates for multi-stage TDL synthesis workflows."""
from __future__ import annotations

from string import Template
from textwrap import dedent


ANALYSIS_PROMPT_TEMPLATE = Template(
    dedent(
        """
        You are a master robot language transpiler and robust parser.
        Your job: (1) detect the manufacturer of the source job file; (2) parse EVERY non-comment line into a structured JSON according to the retrieved parsing rules; (3) never drop unknown params—store them under 'extras'.

        **[Retrieved Parsing Instructions]**
        Treat the content below as the authoritative parsing spec. If multiple variants conflict, prefer the MOST RECENT/LENIENT rules contained in the later part of the text.
        ```
        $retrieved_instructions
        ```

        **Normalization & Lenient Policy (apply BEFORE parsing):**
        L0) Function/constant names are CASE-INSENSITIVE (e.g., movej/MOVEJ/MoveJ are the same).
        L1) Ignore leading/trailing and redundant whitespace/newlines; allow trailing commas in arg lists.
        L2) Treat 'ON'/'OFF' (any case) as 1/0, but preserve the original token under extras.original_token when needed.
        L3) Accept named args in ANY order, and allow positional args when unambiguous. Missing optional args must be omitted (or set to null) — do NOT invent defaults.
        L4) Accept common aliases and normalize them: 'r'→'radius', 'vel' or 'v'→velocity object, 'reference'→'ref'. Preserve the original key under extras.original_key if both appear.
        L5) Inline trailing comments after valid code are ignored. Lines starting with a comment prefix are ignored.
        L6) Numbers may be int/float/scientific (e.g., 3, 3.0, 3., 3e-1). Do NOT reformat pose literals.
        L7) For motion constructors, capture pose calls verbatim (e.g., 'posj(...)', 'posx(...)').
        L8) **Unit Preservation**: When a value has a unit (e.g., `S=150mm/s`, `vel=30%`, `duration=0.5sec`), you MUST capture the value as a string to preserve the unit (e.g., `"150mm/s"`, `"30%"`), not just the number.

        **STRICT OUTPUT CONTRACT:**
        Your final answer MUST be a SINGLE JSON object with EXACTLY TWO top-level keys:
          1) 'manufacturer' (lowercase string: 'hyundai' or 'doosan', etc.),
          2) 'logic' (object with 'initialization', 'main_sequence', 'finalization' arrays of parsed command objects).
        Additionally, INSIDE 'logic', include:
            - 'metadata': {
                "converted_at": "<ISO-8601 timestamp in Asia/Seoul timezone, e.g., 2025-10-02T13:45:12+09:00>",
                "robot": {
                    "manufacturer": "<detected or inferred manufacturer in lowercase>",
                    "model": "<detected robot model string or null if unknown>, ex) HS220, h2017 ..."
                }
            }
            - If any source lines could not be parsed, include 'unparsed_lines': [ ... ] (otherwise omit 'unparsed_lines').
        Do not wrap the JSON with any text. If you provide a code fence, use ```json ... ```.

        **Robustness:**
        - NEVER fail due to unknown/extra args; store them under 'extras'.
        - NEVER drop a non-comment line. If unsure, emit a conservative node with an 'extras.source' copy of the line.
        - Prefer the most lenient interpretations in the retrieved rules when conflicts exist.

        **Source Job File:**
        ```
        $source_job_file
        ```

        **Examples to emulate:**
        Example A (MoveJ with only radius & ra):
          movej(posj(0,0,90,0,90,0), radius=0.00, ra=DR_MV_RA_DUPLICATE)
        → {"command":"MoveJ","parameters":{"pos":"posj(0,0,90,0,90,0)","radius":0.0,"ra":"DR_MV_RA_DUPLICATE","extras":{"ra_literal":"DR_MV_RA_DUPLICATE"}}}
        Example B (Wait DI shortcut):
          wait_digital_input(11,ON)
        → {"command":"WaitForInput","parameters":{"port":11,"value":"ON"}}

        **Final JSON Output:**
        """
    )
)


ARCHITECTURE_PROMPT_TEMPLATE = Template(
    dedent(
        """
        You are a TDL language architect. Your task is to create a TDL architecture blueprint based on a list of required commands and a full TDL syntax reference.

        **1. Full TDL Syntax Reference (from RAG):**
        This contains all possible GOAL and COMMAND definitions.
        ```
        $tdl_syntax_rules
        ```

        **2. Structured Job Logic (from Agent 1):**
        This JSON contains the commands that were actually found in the source job file.
        ```json
        $structured_logic
        ```

        **Your Task:**
        A. From the `Full TDL Syntax Reference`, extract all `goal_templates`.
        B. Look at the `command` names in the `Structured Job Logic`. For each unique command name, find all its corresponding function signatures from the `Full TDL Syntax Reference`.
        C. Create the final JSON output with three keys:
           1. "goal_templates": All GOAL templates.
           2. "spawnable_commands": A list of the specific function signatures you found in step B.
           3. "command_definitions": An object where keys are the signatures from your new list, and values are their full `COMMAND` definitions.

        **Final JSON Output (Extracted and Filtered Architecture):**
        """
    )
)


SYNTHESIS_PROMPT_TEMPLATE = Template(
    dedent(
        """
        You are an intelligent and strict TDL code synthesizer. Your task is to build TDL code and identify the exact command signatures used, following the provided architecture precisely.

        **Reasoning Steps:**
        1.  The `Structured Job Logic` input contains phases ('initialization', 'main_sequence', 'finalization'), each holding a list of operation objects.
        2.  For each operation object, find the single best matching function signature from the `spawnable_commands` list provided in the `TDL Architecture`.
        3.  **CRITICAL SYNTAX RULE**: Create a `SPAWN` command line. The function call inside `SPAWN` **MUST** exactly match the chosen signature's parameter names and order.
        4.  Populate the `GOAL` templates with the correctly formatted `SPAWN` commands.
        5.  Compile a list of the unique function signatures you used.

        **CRITICAL OUTPUT RULE: Your final output must be a single JSON object with two keys:**
        1. "goal_code": A string containing ONLY the populated GOAL blocks.
        2. "used_signatures": A list of the unique function signature strings you used.

        **TDL Architecture (Blueprint):**
        ```json
        $tdl_architecture
        ```

        **Structured Job Logic (Content):**
        ```json
        $structured_logic
        ```

        **Final JSON Output:**
        """
    )
)


def create_analysis_prompt(*, retrieved_instructions: str, source_job_file: str) -> str:
    """Return the formatted prompt for the analysis agent."""

    return ANALYSIS_PROMPT_TEMPLATE.substitute(
        retrieved_instructions=retrieved_instructions,
        source_job_file=source_job_file,
    )


def create_architecture_extraction_prompt(*, tdl_syntax_rules: str, structured_logic: str) -> str:
    """Return the formatted prompt for the architecture extraction agent."""

    return ARCHITECTURE_PROMPT_TEMPLATE.substitute(
        tdl_syntax_rules=tdl_syntax_rules,
        structured_logic=structured_logic,
    )


def create_synthesis_prompt(*, tdl_architecture: str, structured_logic: str) -> str:
    """Return the formatted prompt for the synthesis agent."""

    return SYNTHESIS_PROMPT_TEMPLATE.substitute(
        tdl_architecture=tdl_architecture,
        structured_logic=structured_logic,
    )
