#!/usr/bin/env python3
"""Gemini API 연결 테스트 스크립트

이 스크립트는 Gemini API 키가 올바르게 설정되었는지 확인합니다.

사용법:
    export GEMINI_API_KEY="your-api-key-here"
    python test_gemini_api.py
    
또는:
    GEMINI_API_KEY="your-api-key-here" python test_gemini_api.py
"""

import os
import sys


def print_header(text: str) -> None:
    """Print formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"✗ {text}", file=sys.stderr)


def print_info(text: str) -> None:
    """Print info message."""
    print(f"ℹ {text}")


def test_api_key_setup() -> bool:
    """Test if API key is configured."""
    print_header("1단계: API 키 설정 확인")
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if not api_key:
        print_error("GEMINI_API_KEY 환경변수가 설정되지 않았습니다!")
        print("\n다음과 같이 API 키를 설정해주세요:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nAPI 키 발급 방법:")
        print("  1. https://aistudio.google.com/app/apikey 접속")
        print("  2. 'Create API Key' 버튼 클릭")
        print("  3. 생성된 키를 복사하여 환경변수에 설정")
        return False
    
    # Mask API key for security
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print_success(f"API 키가 설정되어 있습니다: {masked_key}")
    print_info(f"API 키 길이: {len(api_key)} characters")
    
    return True


def test_package_installation() -> bool:
    """Test if required packages are installed."""
    print_header("2단계: 필수 패키지 설치 확인")
    
    try:
        import google.generativeai as genai
        print_success("google-generativeai 패키지가 설치되어 있습니다")
        return True
    except ImportError:
        print_error("google-generativeai 패키지가 설치되지 않았습니다!")
        print("\n다음 명령어로 설치해주세요:")
        print("  pip install google-generativeai")
        return False


def test_api_connection() -> bool:
    """Test actual API connection."""
    print_header("3단계: Gemini API 연결 테스트")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        
        print_info("API 연결 시도 중...")
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            "테스트: 숫자 1을 출력해주세요.",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.0
            )
        )
        
        if response.text.strip():
            print_success("API 연결 성공!")
            print_info(f"응답: {response.text.strip()}")
            return True
        else:
            print_error("API가 빈 응답을 반환했습니다")
            return False
            
    except Exception as e:
        print_error(f"API 연결 실패: {e}")
        print("\n가능한 원인:")
        print("  1. API 키가 올바르지 않습니다")
        print("  2. 네트워크 연결에 문제가 있습니다")
        print("  3. API 할당량이 초과되었습니다")
        print("  4. API 키가 활성화되지 않았습니다")
        print("\n해결 방법:")
        print("  - https://aistudio.google.com/app/apikey 에서 API 키 확인")
        print("  - 새로운 API 키를 생성하여 다시 시도")
        return False


def test_nl2tdl_integration() -> bool:
    """Test integration with NL2TDL system."""
    print_header("4단계: NL2TDL 통합 테스트")
    
    try:
        from nl2tdl.llm_client import GeminiLLM
        
        print_info("GeminiLLM 인스턴스 생성 중...")
        llm = GeminiLLM(model="gemini-1.5-flash")
        
        print_success("GeminiLLM 인스턴스 생성 성공!")
        
        print_info("간단한 요구사항 분석 테스트 중...")
        result = llm.analyze_requirement("로봇을 이용해서 박스를 A에서 B로 이동시켜줘")
        
        print_success("요구사항 분석 성공!")
        print(f"\n분석 결과:")
        print(f"  - 감지된 동작: {result.detected_actions}")
        print(f"  - 객체: {result.objects}")
        print(f"  - 시작 위치: {result.source_location}")
        print(f"  - 목표 위치: {result.target_location}")
        
        return True
        
    except Exception as e:
        print_error(f"통합 테스트 실패: {e}")
        return False


def main() -> int:
    """Run all tests."""
    print_header("Gemini API 연결 테스트")
    print("이 스크립트는 Gemini API가 올바르게 설정되었는지 확인합니다.")
    
    results = []
    
    # Test 1: API key setup
    results.append(test_api_key_setup())
    
    if not results[0]:
        print_header("테스트 중단")
        print("API 키를 먼저 설정해주세요.")
        return 1
    
    # Test 2: Package installation
    results.append(test_package_installation())
    
    if not results[1]:
        print_header("테스트 중단")
        print("필수 패키지를 먼저 설치해주세요.")
        return 1
    
    # Test 3: API connection
    results.append(test_api_connection())
    
    # Test 4: NL2TDL integration
    if results[2]:  # Only run if API connection successful
        results.append(test_nl2tdl_integration())
    
    # Summary
    print_header("테스트 결과 요약")
    
    test_names = [
        "API 키 설정",
        "패키지 설치",
        "API 연결",
        "NL2TDL 통합"
    ]
    
    for i, (name, result) in enumerate(zip(test_names[:len(results)], results), 1):
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{i}. {name}: {status}")
    
    all_passed = all(results)
    
    if all_passed:
        print_header("🎉 모든 테스트 통과!")
        print("Gemini API가 올바르게 설정되었습니다.")
        print("\n프로그램 실행 방법:")
        print("  python main.py --provider gemini --llm-model gemini-1.5-flash -r '로봇으로 박스를 옮겨줘'")
        print("\n또는 환경변수 사용:")
        print("  export NL2TDL_LLM_PROVIDER=gemini")
        print("  export NL2TDL_LLM_MODEL=gemini-1.5-flash")
        print("  python main.py -r '로봇으로 박스를 옮겨줘'")
        return 0
    else:
        print_header("⚠️ 일부 테스트 실패")
        print("위의 에러 메시지를 확인하고 문제를 해결해주세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
