# Gemini API 설정 가이드 (한국어)

이 가이드는 Google Gemini API를 NL2TDL 시스템에 확실하게 연동하는 방법을 설명합니다.

## 📋 목차

1. [API 키 발급](#1-api-키-발급)
2. [패키지 설치](#2-패키지-설치)
3. [API 키 설정](#3-api-키-설정)
4. [연결 테스트](#4-연결-테스트)
5. [프로그램 실행](#5-프로그램-실행)
6. [문제 해결](#6-문제-해결)

---

## 1. API 키 발급

### 단계별 가이드:

1. **Google AI Studio 접속**
   - 브라우저에서 https://aistudio.google.com/app/apikey 열기
   - Google 계정으로 로그인

2. **API 키 생성**
   - "Create API Key" 버튼 클릭
   - 프로젝트 선택 (또는 새 프로젝트 생성)
   - API 키가 생성됨 (예: `AIzaSyABCD1234...`)

3. **API 키 복사**
   - 생성된 API 키를 안전한 곳에 복사
   - ⚠️ **중요**: API 키는 비밀번호처럼 관리하세요!

### 무료 할당량:
- 분당 15 요청
- 일일 1,500 요청
- 대부분의 개발/테스트 용도로 충분합니다

---

## 2. 패키지 설치

Google Gemini API를 사용하기 위해 필수 패키지를 설치합니다:

```bash
pip install google-generativeai
```

---

## 3. API 키 설정

API 키를 설정하는 방법은 여러 가지가 있습니다:

### 방법 1: 환경변수 파일 사용 (추천)

1. `.env.example` 파일을 `.env`로 복사:
   ```bash
   cp .env.example .env
   ```

2. `.env` 파일을 편집하여 API 키 입력:
   ```bash
   GEMINI_API_KEY=여기에-실제-API-키-입력
   NL2TDL_LLM_PROVIDER=gemini
   NL2TDL_LLM_MODEL=gemini-1.5-flash
   ```

3. 환경변수 로드:
   ```bash
   source .env
   # 또는
   export $(cat .env | xargs)
   ```

### 방법 2: 직접 export (간단한 테스트용)

```bash
export GEMINI_API_KEY="여기에-실제-API-키-입력"
export NL2TDL_LLM_PROVIDER=gemini
export NL2TDL_LLM_MODEL=gemini-1.5-flash
```

### 방법 3: 명령어 실행 시 설정

```bash
GEMINI_API_KEY="여기에-실제-API-키-입력" python main.py --provider gemini -r "테스트"
```

---

## 4. 연결 테스트

API가 제대로 설정되었는지 확인하는 테스트 스크립트를 실행합니다:

```bash
python test_gemini_api.py
```

### 성공적인 출력 예시:

```
======================================================================
  1단계: API 키 설정 확인
======================================================================

✓ API 키가 설정되어 있습니다: AIzaSyAB...xyz4
ℹ API 키 길이: 39 characters

======================================================================
  2단계: 필수 패키지 설치 확인
======================================================================

✓ google-generativeai 패키지가 설치되어 있습니다

======================================================================
  3단계: Gemini API 연결 테스트
======================================================================

ℹ API 연결 시도 중...
✓ API 연결 성공!
ℹ 응답: 1

======================================================================
  4단계: NL2TDL 통합 테스트
======================================================================

ℹ GeminiLLM 인스턴스 생성 중...
✓ Gemini API 연결 성공! (모델: gemini-1.5-flash)
✓ GeminiLLM 인스턴스 생성 성공!
ℹ 간단한 요구사항 분석 테스트 중...
✓ 요구사항 분석 성공!

분석 결과:
  - 감지된 동작: ['move', 'transport']
  - 객체: ['박스']
  - 시작 위치: A
  - 목표 위치: B

======================================================================
  테스트 결과 요약
======================================================================

1. API 키 설정: ✓ 성공
2. 패키지 설치: ✓ 성공
3. API 연결: ✓ 성공
4. NL2TDL 통합: ✓ 성공

======================================================================
  🎉 모든 테스트 통과!
======================================================================

Gemini API가 올바르게 설정되었습니다.
```

### 실패 시 나타나는 오류:

테스트 스크립트는 문제를 명확하게 설명하고 해결 방법을 제시합니다:

```
✗ GEMINI_API_KEY 환경변수가 설정되지 않았습니다!

다음과 같이 API 키를 설정해주세요:
  export GEMINI_API_KEY='your-api-key-here'

API 키 발급 방법:
  1. https://aistudio.google.com/app/apikey 접속
  2. 'Create API Key' 버튼 클릭
  3. 생성된 키를 복사하여 환경변수에 설정
```

---

## 5. 프로그램 실행

테스트가 성공했다면 이제 실제 프로그램을 실행할 수 있습니다!

### 예시 1: 기본 사용

```bash
python main.py --provider gemini -r "로봇을 이용해서 박스를 A에서 B로 옮겨줘"
```

### 예시 2: 환경변수 사용

```bash
# 환경변수 설정
export NL2TDL_LLM_PROVIDER=gemini
export NL2TDL_LLM_MODEL=gemini-1.5-flash

# 실행
python main.py -r "로봇으로 10kg 박스를 3미터 거리로 이동"
```

### 예시 3: 다른 모델 사용

```bash
# Gemini Pro 모델 (더 강력하지만 느림)
python main.py --provider gemini --llm-model gemini-1.5-pro -r "복잡한 작업 요구사항"

# 실험적 최신 모델
python main.py --provider gemini --llm-model gemini-2.0-flash-exp -r "테스트"
```

### 예시 4: 파일에서 요구사항 읽기

```bash
echo "로봇으로 박스를 창고 A에서 창고 B로 이동시켜줘" > requirement.txt
python main.py --provider gemini -f requirement.txt
```

### 예시 5: TDL만 출력

```bash
python main.py --provider gemini --tdl-only -r "박스 이동"
```

### 예시 6: TDL을 파일로 저장

```bash
python main.py --provider gemini -r "박스 이동" --write-tdl output.tdl
```

---

## 6. 문제 해결

### 문제 1: API 키 오류

**증상**:
```
ERROR: Gemini API 키가 설정되지 않았습니다!
```

**해결 방법**:
1. API 키가 올바르게 설정되었는지 확인:
   ```bash
   echo $GEMINI_API_KEY
   ```
2. 출력이 비어있다면 다시 설정:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

---

### 문제 2: 패키지 없음

**증상**:
```
google-generativeai is required for GeminiLLM
```

**해결 방법**:
```bash
pip install google-generativeai
```

---

### 문제 3: API 연결 실패

**증상**:
```
✗ API 연결 실패: [403] API key not valid
```

**해결 방법**:
1. API 키가 올바른지 확인
2. https://aistudio.google.com/app/apikey 에서 새 API 키 생성
3. API 키에 공백이나 특수문자가 없는지 확인

---

### 문제 4: 할당량 초과

**증상**:
```
Resource has been exhausted (e.g. check quota)
```

**해결 방법**:
1. 잠시 기다렸다가 다시 시도 (분당 제한)
2. 다음 날 다시 시도 (일일 제한)
3. 유료 플랜 고려

---

### 문제 5: 네트워크 오류

**증상**:
```
Failed to connect to generativelanguage.googleapis.com
```

**해결 방법**:
1. 인터넷 연결 확인
2. 방화벽 설정 확인
3. 프록시 설정 확인

---

## 📊 지원되는 모델

| 모델 | 속도 | 품질 | 추천 용도 |
|------|------|------|-----------|
| `gemini-1.5-flash` | ⚡⚡⚡ | ⭐⭐⭐ | 일반적인 작업 (추천) |
| `gemini-1.5-pro` | ⚡⚡ | ⭐⭐⭐⭐ | 복잡한 분석 |
| `gemini-2.0-flash-exp` | ⚡⚡⚡ | ⭐⭐⭐⭐ | 최신 기능 테스트 |

---

## 💡 팁

1. **API 키 보안**
   - API 키를 코드에 직접 넣지 마세요
   - `.env` 파일을 `.gitignore`에 추가하세요
   - 공개 저장소에 API 키를 올리지 마세요

2. **효율적인 사용**
   - `gemini-1.5-flash` 모델이 대부분의 경우 충분합니다
   - 개발 중에는 temperature=0.0 (결정론적 응답)
   - 할당량 관리를 위해 캐싱 고려

3. **디버깅**
   - `test_gemini_api.py`를 먼저 실행하여 설정 확인
   - 에러 메시지를 주의깊게 읽기
   - 테스트 스크립트가 자세한 가이드 제공

---

## 🔗 참고 링크

- [Gemini API 문서](https://ai.google.dev/docs)
- [API 키 관리](https://aistudio.google.com/app/apikey)
- [가격 및 할당량](https://ai.google.dev/pricing)
- [커뮤니티 포럼](https://discuss.ai.google.dev/)

---

## ✅ 체크리스트

설정이 완료되었는지 확인하세요:

- [ ] API 키 발급 완료
- [ ] `google-generativeai` 패키지 설치
- [ ] `GEMINI_API_KEY` 환경변수 설정
- [ ] `test_gemini_api.py` 실행하여 모든 테스트 통과
- [ ] 실제 프로그램 실행하여 결과 확인

모든 항목을 체크했다면 준비 완료! 🎉
