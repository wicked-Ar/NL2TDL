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

To persist the generated artifacts, you can additionally request on-disk outputs:

```bash
python main.py -r "박스를 이동해줘" --write-tdl --write-job
```

- `--write-tdl` saves the raw TDL script (default filename: `tdl_output.tdl`).
- `--write-job` exports a vendor-oriented job file that approximates Doosan DRL syntax for quick hand-off to programming tools (default filename: `job_output.job`).

### Command-line Arguments

The CLI exposes additional switches so you can customize inputs, robot metadata, and LLM behavior:

| Flag | Purpose |
|------|---------|
| `-r, --requirement` | Directly pass the natural-language instruction on the command line. If omitted the tool checks `--file`, then STDIN, and finally prompts interactively. |
| `-f, --file` | Read the requirement text from a UTF-8 file. |
| `--manufacturer` | Override the robot manufacturer recorded in the TDL header (default: `doosan`). |
| `--model-name` | Override the robot model stored in the TDL header (default: `h2017`). |
| `--robot-db` | Provide a custom robot specification database JSON used by the selector (default: `robots_db.json`). |
| `--tdl-only` | Print only the generated TDL without the analysis/validation sections. |
| `--write-tdl` | Persist the TDL text to a file. If no path is provided, the tool saves to `tdl_output.tdl`. |
| `--write-job` | Persist a Doosan-style job approximation generated from the TDL. If no path is provided, the tool saves to `job_output.job`. |
| `--provider` | Choose an explicit LLM backend (`ollama`, `hf`, `gemini`, or `none`). When omitted the provider is inferred from the environment. |
| `--llm-model` | Specify the model identifier for the chosen provider. |
| `--llm-endpoint` | Point an Ollama client to a non-default base URL. |
| `--llm-device` | Select the Hugging Face execution device (e.g., `cuda:0`). |

## Optional: LLM Integration

You can enable LLM-assisted requirement analysis to improve parsing quality. Three providers are supported:

### Option 1: Google Gemini API (Recommended - Cloud-based, Easy Setup)

**장점**: 설치 불필요, 빠른 응답, 무료 할당량 제공

1. **API 키 발급**:
   - https://aistudio.google.com/app/apikey 접속
   - "Create API Key" 버튼 클릭
   - 생성된 API 키 복사

2. **패키지 설치**:
   ```bash
   pip install google-generativeai
   ```

3. **API 키 설정 및 실행**:
   ```bash
   # API 키 설정
   export GEMINI_API_KEY="your-api-key-here"
   
   # 방법 1: 환경변수 사용
   export NL2TDL_LLM_PROVIDER=gemini
   export NL2TDL_LLM_MODEL=gemini-1.5-flash  # 또는 gemini-1.5-pro
   python main.py -r "로봇으로 박스를 A에서 B로 옮겨줘"
   
   # 방법 2: 명령줄 인자 사용
   python main.py --provider gemini --llm-model gemini-1.5-flash -r "로봇으로 박스를 A에서 B로 옮겨줘"
   ```

4. **연결 테스트**:
   ```bash
   python test_gemini_api.py
   ```
   
   테스트 스크립트가 다음을 확인합니다:
   - ✓ API 키가 올바르게 설정되었는지
   - ✓ 필수 패키지가 설치되었는지
   - ✓ Gemini API 연결이 작동하는지
   - ✓ NL2TDL 시스템과 통합이 되는지

**사용 가능한 모델**:
- `gemini-1.5-flash` (추천): 빠르고 효율적, 대부분의 작업에 적합
- `gemini-1.5-pro`: 더 강력하지만 느림, 복잡한 분석에 적합
- `gemini-2.0-flash-exp`: 실험적 최신 모델

**할당량**: 무료 tier에서 분당 15 요청, 일일 1,500 요청 제공

---

### Option 2: Ollama (Local)

로컬에서 실행되는 모델을 사용하려면:

1. Install Ollama and pull a Gemma model (e.g., `gemma:2b`).
2. Set environment variables before running:
   ```bash
   export NL2TDL_LLM_PROVIDER=ollama
   export NL2TDL_LLM_MODEL=gemma:2b
   export NL2TDL_LLM_ENDPOINT=http://localhost:11434
   python main.py
   ```

---

### Option 3: Hugging Face Transformers (Local)

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

---

### Fallback Behavior

- If environment variables are not set or the model call fails, the system falls back to the built-in heuristic parser.
- The LLM is prompted to output a strict JSON with fields accepted by the pipeline (actions, objects, locations, constraints like `payload_kg`, `reach_m`).
