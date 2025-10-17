"""Pluggable LLM clients for requirement analysis.

Supports:
- Ollama (local) – tested with Gemma models (e.g., "gemma:2b", "gemma2:2b")
- Hugging Face Transformers (optional) – e.g., "google/gemma-2b-it" via text-generation pipeline
- Google Gemini API – e.g., "gemini-1.5-flash" or "gemini-1.5-pro" (requires API key)

Usage is typically indirect via `get_llm_from_env()` and passing into
`analyze_requirement(requirement, llm=...)`.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .models import RequirementAnalysisResult


ANALYSIS_JSON_INSTRUCTIONS = (
    "You are a planner. Convert the user's instruction into a strict JSON object "
    "with keys: source_requirement (string), detected_actions (array of strings), "
    "objects (array of strings), source_location (string|null), target_location (string|null), "
    "constraints (object with numeric fields e.g., payload_kg, reach_m). "
    "Only output JSON, no extra text."
)


def _extract_first_json_block(text: str) -> str:
    """Extract the first top-level JSON object from text.

    This is robust against models adding prose around the JSON.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start found in model output")
    # naive stack-based matching
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unbalanced JSON braces in model output")


def _coerce_analysis_dict(payload: Dict[str, Any]) -> RequirementAnalysisResult:
    src = str(payload.get("source_requirement", ""))
    actions = [str(a) for a in (payload.get("detected_actions") or [])]
    objects = [str(o) for o in (payload.get("objects") or [])]
    source_location = payload.get("source_location")
    target_location = payload.get("target_location")
    source_location = None if source_location in ("", None) else str(source_location)
    target_location = None if target_location in ("", None) else str(target_location)

    constraints_obj = payload.get("constraints") or {}
    constraints: Dict[str, float] = {}
    for k, v in constraints_obj.items():
        try:
            constraints[str(k)] = float(v)
        except Exception:
            # ignore non-numeric
            continue

    return RequirementAnalysisResult(
        source_requirement=src,
        detected_actions=actions or ["analyze"],
        objects=objects,
        source_location=source_location,
        target_location=target_location,
        constraints=constraints,
    )


@dataclass
class BaseLLM:
    """Abstract base for LLM providers."""

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        raise NotImplementedError

    def generate_json(self, prompt: str, max_output_tokens: int = 2048) -> str:
        """Generate a JSON payload from the model based on the given prompt.

        Implementations should return a string representation of the first
        well-formed JSON object contained in the model's response. The default
        implementation raises ``NotImplementedError`` so that concrete LLM
        clients can opt-in to more advanced prompting workflows.
        """

        raise NotImplementedError


@dataclass
class OllamaLLM(BaseLLM):
    model: str = "gemma:2b"
    endpoint: str = "http://localhost:11434"
    # use /api/generate to keep things simple and avoid chat formatting

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        prompt = (
            f"{ANALYSIS_JSON_INSTRUCTIONS}\n\n"
            f"User Instruction: {requirement}\n"
        )
        url = self.endpoint.rstrip("/") + "/api/generate"
        body = {"model": self.model, "prompt": prompt, "stream": False}

        # Prefer stdlib to avoid hard dependency on requests
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        output = data.get("response") or data.get("output") or ""
        json_text = _extract_first_json_block(output)
        analysis_payload = json.loads(json_text)
        return _coerce_analysis_dict(analysis_payload)


@dataclass
class HuggingFaceLLM(BaseLLM):
    model: str = "google/gemma-2b-it"
    device: Optional[str] = None  # e.g., "cuda:0" or "cpu"

    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        try:
            from transformers import pipeline  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "transformers is required for HuggingFaceLLM. Install with `pip install transformers`"
            ) from e

        generator = pipeline(
            task="text-generation",
            model=self.model,
            device=self.device if self.device is not None else -1,
            max_new_tokens=512,
            do_sample=False,
        )

        prompt = (
            f"{ANALYSIS_JSON_INSTRUCTIONS}\n\n"
            f"User Instruction: {requirement}\n"
        )
        outputs = generator(prompt)
        text = outputs[0]["generated_text"] if outputs else ""
        json_text = _extract_first_json_block(text)
        analysis_payload = json.loads(json_text)
        return _coerce_analysis_dict(analysis_payload)


@dataclass
class GeminiLLM(BaseLLM):
    """Google Gemini API client with explicit API key configuration.
    
    Requires:
    - google-generativeai package: pip install google-generativeai
    - API key set via environment variable: GEMINI_API_KEY
    
    Example usage:
        export GEMINI_API_KEY="your-api-key-here"
        python main.py --provider gemini --llm-model gemini-1.5-flash
    """
    model: str = "gemini-1.5-flash"
    api_key: Optional[str] = None
    temperature: float = 0.0
    
    def __post_init__(self):
        """Validate API key and configure Gemini client."""
        # Try to get API key from instance or environment
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        
        if not self.api_key:
            print("\n" + "="*70, file=sys.stderr)
            print("ERROR: Gemini API 키가 설정되지 않았습니다!", file=sys.stderr)
            print("="*70, file=sys.stderr)
            print("\n다음 중 하나의 방법으로 API 키를 설정해주세요:", file=sys.stderr)
            print("\n1. 환경변수 설정:", file=sys.stderr)
            print("   export GEMINI_API_KEY='your-api-key-here'", file=sys.stderr)
            print("\n2. 프로그램 실행 시 설정:", file=sys.stderr)
            print("   GEMINI_API_KEY='your-api-key-here' python main.py --provider gemini", file=sys.stderr)
            print("\n3. API 키 발급 방법:", file=sys.stderr)
            print("   - https://aistudio.google.com/app/apikey 에서 발급", file=sys.stderr)
            print("   - 무료로 사용 가능 (일일 할당량 제한 있음)", file=sys.stderr)
            print("\n" + "="*70 + "\n", file=sys.stderr)
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Get your key at: https://aistudio.google.com/app/apikey"
            )
        
        # Import and configure genai
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "google-generativeai is required for GeminiLLM. "
                "Install with: pip install google-generativeai"
            ) from e
        
        genai.configure(api_key=self.api_key)
        self._genai = genai
        self._model = genai.GenerativeModel(self.model)
        
        # Test connection
        print(f"✓ Gemini API 연결 성공! (모델: {self.model})", file=sys.stderr)

    def _build_safety_settings(self):
        """Return permissive safety settings used for generation calls."""

        return {
            self._genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT:
                self._genai.types.HarmBlockThreshold.BLOCK_NONE,
            self._genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH:
                self._genai.types.HarmBlockThreshold.BLOCK_NONE,
            self._genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:
                self._genai.types.HarmBlockThreshold.BLOCK_NONE,
            self._genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
                self._genai.types.HarmBlockThreshold.BLOCK_NONE,
        }

    def test_connection(self) -> bool:
        """Test the API connection with a simple prompt.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            response = self._model.generate_content(
                "테스트: 숫자 1을 출력해주세요.",
                generation_config=self._genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.0
                )
            )
            return bool(response.text.strip())
        except Exception as e:
            print(f"\n✗ API 연결 테스트 실패: {e}", file=sys.stderr)
            return False
    
    def analyze_requirement(self, requirement: str) -> RequirementAnalysisResult:
        """Analyze requirement using Gemini API."""
        prompt = (
            f"{ANALYSIS_JSON_INSTRUCTIONS}\n\n"
            f"User Instruction: {requirement}\n"
        )
        
        try:
            # Configure safety settings to avoid blocking
            safety_settings = self._build_safety_settings()

            response = self._model.generate_content(
                prompt,
                generation_config=self._genai.types.GenerationConfig(
                    max_output_tokens=2048,
                    temperature=self.temperature
                ),
                safety_settings=safety_settings
            )
            
            if not response.parts:
                finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                raise ValueError(f"API returned no content. Finish reason: {finish_reason}")
            
            output = response.text.strip()
            json_text = _extract_first_json_block(output)
            analysis_payload = json.loads(json_text)
            return _coerce_analysis_dict(analysis_payload)
            
        except Exception as e:
            print(f"\n✗ Gemini API 호출 중 오류 발생: {e}", file=sys.stderr)
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    def generate_json(self, prompt: str, max_output_tokens: int = 2048) -> str:
        """Generate JSON text for advanced prompting workflows."""

        try:
            safety_settings = self._build_safety_settings()
            response = self._model.generate_content(
                prompt,
                generation_config=self._genai.types.GenerationConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=self.temperature,
                ),
                safety_settings=safety_settings,
            )

            if not response.parts:
                finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                raise ValueError(f"API returned no content. Finish reason: {finish_reason}")

            output = response.text.strip()
            return _extract_first_json_block(output)
        except Exception as e:
            raise RuntimeError(f"Gemini JSON generation failed: {e}") from e


def get_llm_from_env() -> BaseLLM | None:
    """Get LLM instance from environment variables.
    
    Supported providers:
    - ollama: Local Ollama server (NL2TDL_LLM_PROVIDER=ollama)
    - hf/huggingface: HuggingFace Transformers (NL2TDL_LLM_PROVIDER=hf)
    - gemini: Google Gemini API (NL2TDL_LLM_PROVIDER=gemini, requires GEMINI_API_KEY)
    
    Returns:
        BaseLLM instance or None if no provider is configured.
    """
    provider = os.getenv("NL2TDL_LLM_PROVIDER", "").strip().lower()
    if not provider:
        return None

    if provider == "ollama":
        model = os.getenv("NL2TDL_LLM_MODEL", "gemma:2b")
        endpoint = os.getenv("NL2TDL_LLM_ENDPOINT", "http://localhost:11434")
        return OllamaLLM(model=model, endpoint=endpoint)

    if provider in ("hf", "huggingface"):
        model = os.getenv("NL2TDL_LLM_MODEL", "google/gemma-2b-it")
        device = os.getenv("NL2TDL_LLM_DEVICE")
        return HuggingFaceLLM(model=model, device=device)
    
    if provider == "gemini":
        model = os.getenv("NL2TDL_LLM_MODEL", "gemini-1.5-flash")
        api_key = os.getenv("GEMINI_API_KEY")
        temperature = float(os.getenv("NL2TDL_LLM_TEMPERATURE", "0.0"))
        return GeminiLLM(model=model, api_key=api_key, temperature=temperature)

    # Unknown provider -> disabled
    return None
