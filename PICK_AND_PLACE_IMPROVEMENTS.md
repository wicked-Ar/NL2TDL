# Pick-and-Place TDL 생성 개선 사항

## 문제점 분석

기존 시스템은 "로봇X를 이용해서 박스Y를 A에서 B로 옮겨줘"와 같은 한국어 pick-and-place 요구사항을 처리할 때 다음과 같은 문제가 있었습니다:

1. **불완전한 동작 시퀀스**: 단일 `MoveLinear` 명령만 생성
2. **한국어 미지원**: 한국어 키워드를 인식하지 못함
3. **복합 동작 미인식**: "옮기다"가 pick+move+place의 조합임을 인식하지 못함
4. **위치 정보 미활용**: A, B 위치를 파싱했지만 좌표로 변환하지 않음

## 개선 사항

### 1. 한국어 키워드 지원 강화

**파일**: `nl2tdl/requirement_analysis.py`

```python
ACTION_KEYWORDS = {
    "pick": ["pick", "grasp", "grab", "collect", "lift", "잡", "집", "들", "픽업"],
    "place": ["place", "put", "set", "drop", "놓", "내려놓", "배치", "플레이스"],
    "move": ["move", "carry", "deliver", "이동", "운반"],
    "wait": ["wait", "hold", "대기", "기다"],
    # 복합 액션: transfer는 pick+move+place를 의미
    "transfer": ["옮기", "옮겨", "옮긴", "전달", "이송", "transfer"],
}
```

- 한국어 동사의 다양한 활용형 지원 (옮기다 → 옮겨, 옮기, 옮긴)
- 객체 및 위치 패턴도 한국어 지원

### 2. 복합 동작 감지 및 확장

"옮기다"와 같은 복합 동작을 감지하면 자동으로 pick+move+place로 확장:

```python
if has_transfer:
    # "옮기다" 감지 시 전체 pick-and-place 시퀀스 생성
    for action in ["pick", "move", "place"]:
        if action not in actions:
            actions.append(action)
```

### 3. 완전한 Pick-and-Place 시퀀스 생성

**파일**: `nl2tdl/tdl_generator.py`

이제 다음과 같은 8단계 시퀀스를 생성합니다:

1. **Approach Source** (소스 위 접근): 안전한 높이에서 소스 위치로 이동
2. **Move to Grasp** (그립 위치 이동): 객체를 잡을 수 있는 높이로 하강
3. **Grasp** (그립): 그리퍼로 객체 잡기
4. **Lift** (들어올림): 객체를 들어올려 충돌 방지
5. **Move to Target** (타겟 이동): 타겟 위치 위로 이동
6. **Lower** (내림): 타겟 위치로 하강
7. **Release** (릴리스): 그리퍼 열어 객체 놓기
8. **Retract** (후퇴): 안전한 높이로 후퇴

### 4. 위치-좌표 매핑 시스템

명명된 위치를 실제 로봇 좌표로 변환:

```python
DEFAULT_LOCATION_MAP = {
    "a": (0, 0, 50, 0, 0, 0),
    "b": (300, 200, 50, 0, 0, 0),
    "home": (0, 0, 200, 0, 0, 0),
    "pickup": (100, 0, 50, 0, 0, 0),
    "dropoff": (100, 300, 50, 0, 0, 0),
}
```

## 결과 비교

### 이전 (문제가 있던 버전)

```
GOAL Execute_Process() {
    // Execute primary task sequence
    SPAWN MoveLinear(PosX(100,200,300,0,0,0), 100, 50, "gripper", 0.1)
}
```

### 개선 후 (현재 버전)

```
GOAL Execute_Process() {
    // Transfer 박스Y from A to B
    SPAWN MoveLinear(PosX(0,0,150,0,0,0), 100, 50, "gripper", 0.1)  // Approach source_A (above)
    SPAWN MoveLinear(PosX(0,0,60,0,0,0), 50, 30, "gripper", 0.0)  // Move to source_A (grasp height)
    SPAWN GraspObject(40)  // Close gripper
    SPAWN MoveLinear(PosX(0,0,150,0,0,0), 100, 50, "gripper", 0.1)  // Lift from source_A
    SPAWN MoveLinear(PosX(300,200,150,0,0,0), 100, 50, "gripper", 0.1)  // Move to target_B (above)
    SPAWN MoveLinear(PosX(300,200,60,0,0,0), 50, 30, "gripper", 0.0)  // Lower to target_B (place height)
    SPAWN ReleaseObject()  // Open gripper
    SPAWN MoveLinear(PosX(300,200,150,0,0,0), 100, 50, "gripper", 0.1)  // Retract from target_B
}
```

## 테스트 예시

### 한국어 입력
```bash
python3 main.py --provider none -r "로봇X를 이용해서 박스Y를 A에서 B로 옮겨줘"
```

**결과**:
- ✅ 액션 감지: `['pick', 'move', 'place']`
- ✅ 객체 감지: `['박스', '로봇X', '박스Y']`
- ✅ 위치 파싱: `source='A', target='B'`
- ✅ 완전한 8단계 시퀀스 생성

### 영어 입력
```bash
python3 main.py --provider none -r "Pick the box from home and place it at B"
```

**결과**:
- ✅ 액션 감지: `['pick', 'place']`
- ✅ 객체 감지: `['box']`
- ✅ 완전한 pick-and-place 시퀀스 생성

## 추가 개선 가능 사항

1. **동적 위치 학습**: 사용자 정의 위치를 런타임에 추가
2. **경로 최적화**: 중간 경유점 자동 생성
3. **장애물 회피**: 안전 경로 계산
4. **다중 객체**: 여러 객체를 순차적으로 이동
5. **조건부 로직**: "만약 센서가 감지되면..." 등의 조건 처리

## 사용 방법

### 휴리스틱 모드 (LLM 없이)
```bash
python3 main.py --provider none -r "박스를 A에서 B로 옮겨줘"
```

### Gemini 모드 (더 정확한 파싱)
```bash
export GEMINI_API_KEY='your-api-key'
python3 main.py --provider gemini -r "박스를 A에서 B로 옮겨줘"
```

### 위치 커스터마이징

`nl2tdl/tdl_generator.py`의 `DEFAULT_LOCATION_MAP`을 수정하여 프로젝트별 위치를 정의할 수 있습니다:

```python
DEFAULT_LOCATION_MAP = {
    "station1": (100, 0, 50, 0, 0, 0),
    "station2": (200, 100, 50, 0, 0, 0),
    "conveyor": (300, 200, 50, 0, 0, 0),
}
```

## 참고사항

- 좌표는 mm 단위입니다
- 기본 안전 높이: 100mm (충돌 방지)
- 기본 그립 높이: 10mm (객체 위)
- 속도/가속도는 로봇 사양에 맞게 조정 가능
