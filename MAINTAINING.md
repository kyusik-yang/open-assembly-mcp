# Maintaining open-assembly-mcp

이 문서는 패키지를 유지보수하는 절차를 정리한 것입니다.
Claude Code와 함께 작업하는 방법도 포함합니다.

---

## 프로젝트 구조

```
open-assembly-mcp/
├── data_go_mcp/open_assembly/
│   ├── client.py        # 열린국회정보 API httpx 클라이언트 (엔드포인트, 파싱)
│   ├── server.py        # FastMCP 서버 + 도구 정의 (8개 @mcp.tool)
│   └── setup_cli.py     # --setup 위저드 (Claude Desktop config 자동 설정)
├── tests/
│   ├── test_client.py   # API 응답 파싱 단위 테스트 (mock)
│   └── test_server.py   # 각 도구 통합 테스트 (mock)
├── .github/workflows/
│   └── publish.yml      # v* 태그 push → 자동 PyPI 배포
├── pyproject.toml       # 패키지 메타데이터, 의존성, 버전
└── MAINTAINING.md       # 이 파일
```

---

## 로컬 개발 환경 설정

```bash
cd open-assembly-mcp

# 의존성 설치 (dev 포함)
uv sync --group dev

# .env 파일 생성
cp .env.example .env
# ASSEMBLY_API_KEY=your-key 추가

# 테스트 실행
uv run pytest tests/ -v

# 서버 로컬 실행 (MCP inspector로 테스트할 때)
ASSEMBLY_API_KEY=your-key uv run python -m data_go_mcp.open_assembly.server
```

---

## 버전 관리 규칙 (Semantic Versioning)

```
v MAJOR . MINOR . PATCH
      0 . 2   . 1

PATCH (0.2.1 → 0.2.2): 버그 수정, 문서 수정, 설치 스크립트 개선
MINOR (0.2.x → 0.3.0): 새 API 도구 추가, 기존 도구 파라미터 추가
MAJOR (0.x.y → 1.0.0): API 호환성이 깨지는 변경 (도구 이름 변경 등)
```

---

## 릴리즈 절차 (변경 → PyPI 배포)

```bash
# 1. pyproject.toml 버전 올리기
# version = "0.2.1" → "0.2.2"

# 2. 테스트 통과 확인
uv run pytest tests/ -v

# 3. 빌드 확인
uv build

# 4. 커밋
git add .
git commit -m "feat: 변경 내용 요약"
git push origin main

# 5. 태그 생성 → GitHub Actions가 자동으로 PyPI 배포
git tag v0.2.2
git push origin v0.2.2
```

GitHub Actions가 테스트 → 빌드 → `uv publish` 순서로 실행합니다.
배포 결과: https://github.com/kyusik-yang/open-assembly-mcp/actions

---

## 자주 하는 작업

### 새 API 도구 추가하기

열린국회정보에 새 엔드포인트가 생기거나, 기존 데이터를 새 방식으로 노출하고 싶을 때.

**1. `client.py`에 엔드포인트 상수 추가**
```python
EP_NEW_THING = "endpoint_code_here"   # 열린국회정보 API 엔드포인트 코드
```

**2. `client.py`에 메서드 추가**
```python
async def get_new_thing(self, age: str, some_param: Optional[str] = None, ...) -> tuple[list[dict], int]:
    return await self._get(EP_NEW_THING, {
        "AGE": age,
        "SOME_PARAM": some_param,
        "pIndex": page,
        "pSize": page_size,
    })
```

**3. `server.py`에 `@mcp.tool()` 추가**
```python
@mcp.tool()
async def get_new_thing(age: str, ...) -> dict[str, Any]:
    """
    한글 설명 (Claude가 도구를 선택할 때 이 설명을 읽습니다).

    Args:
        age: 대수 — 필수
        ...
    Returns:
        ...
    """
    async with AssemblyAPIClient() as client:
        rows, total = await client.get_new_thing(age=age, ...)
        return {"items": rows, "total_count": total, ...}
```

**4. `tests/test_server.py`에 테스트 추가**
기존 테스트 패턴 복사해서 mock으로 작성.

**5. 버전 올리고 릴리즈** (MINOR 버전)

---

### 기존 도구에 파라미터 추가하기

예: `search_bills`에 `status` 필터 추가.

1. `client.py` 해당 메서드 파라미터 추가
2. `server.py` `@mcp.tool` 함수 파라미터 추가 + docstring 업데이트
3. 테스트 추가
4. PATCH 버전 올리고 릴리즈

---

### 의존성 업데이트

```bash
# 최신 버전으로 업데이트
uv lock --upgrade

# 특정 패키지만
uv lock --upgrade-package httpx

# 테스트 확인
uv run pytest tests/ -v

# 커밋 후 PATCH 릴리즈
```

---

### 버그 수정

1. 버그 재현하는 테스트 먼저 작성
2. 수정
3. 테스트 통과 확인
4. PATCH 버전 올리고 릴리즈

---

## 엔드포인트 참고

열린국회정보 API의 실제 엔드포인트 코드는 불투명한 문자열입니다.
현재 확인된 코드는 `client.py` 상단에 주석과 함께 정리되어 있습니다.

```python
EP_BILLS          = "nzmimeepazxkubdpn"   # 국회의원 발의법률안
EP_BILL_DETAIL    = "ALLBILL"             # 의안정보 통합
EP_BILL_REVIEW    = "nwbpacrgavhjryiph"   # 의안 처리·심사정보
EP_MEMBER         = "nwvrqwxyaytdsfvhu"   # 국회의원 정보
EP_VOTE           = "ncocpgfiaoituanbr"   # 본회의 표결현황 (집계)
EP_BILL_PROPOSERS = "BILLINFOPPSR"        # 공동발의자
EP_MEMBER_VOTES   = "nojepdqqaweusdfbi"  # 개인별 표결 (BILL_ID + AGE 필요)
```

새 엔드포인트가 필요하면 [open.assembly.go.kr](https://open.assembly.go.kr) →
API 목록에서 확인하거나, 기존 코드를 참고해 브라우저 네트워크 탭으로 확인 가능합니다.

---

## Claude Code와 함께 작업하기

이 저장소는 Claude Code로 대부분의 작업을 할 수 있습니다.
`open-assembly-mcp/` 폴더에서 `claude` 실행하거나,
상위 `kyusik-research/` 에서 실행 후 경로를 명시하면 됩니다.

**Claude에게 효과적으로 요청하는 방법:**

| 작업 | 요청 예시 |
|---|---|
| 새 도구 추가 | "열린국회정보 API에 `nXXXXXXX` 엔드포인트로 위원회 회의록 조회 도구 추가해줘. 파라미터는 age, committee_name" |
| 버그 수정 | "search_bills에서 proc_result 파라미터가 빈 문자열일 때 API 에러 나는 거 수정해줘" |
| 버전 릴리즈 | "v0.2.2로 릴리즈해줘. 변경사항: setup_cli 개선" |
| 테스트 추가 | "get_member_votes에서 빈 결과 반환할 때 처리하는 테스트 추가해줘" |
| 의존성 업데이트 | "httpx 최신 버전으로 업데이트하고 테스트 돌려줘" |

**Claude가 작업할 때 하는 일:**
1. 관련 파일 읽기 (`client.py`, `server.py`, 테스트)
2. 기존 패턴 파악
3. 변경 최소화 원칙으로 수정
4. 로컬 테스트 실행 확인
5. 커밋 메시지 작성
6. 태그가 필요하면 요청해서 확인 후 push

---

## 문제 해결

### PyPI 배포 실패

```
# Actions 탭에서 로그 확인
# https://github.com/kyusik-yang/open-assembly-mcp/actions

# 가장 흔한 원인:
# 1. 같은 버전이 이미 존재 → pyproject.toml 버전 올리기
# 2. 테스트 실패 → uv run pytest 로컬 확인
# 3. Trusted Publisher 설정 문제 → pypi.org → Publishing 확인
```

### 테스트 실패

```bash
# 특정 테스트만 실행
uv run pytest tests/test_client.py::TestSearchBills -v

# 상세 출력
uv run pytest tests/ -v -s
```

### API 응답 변경 (열린국회정보 필드 추가/삭제)

열린국회정보 API는 필드가 추가되거나 이름이 바뀔 수 있습니다.
에러가 나면 `client.py`의 `_parse()` 메서드와 해당 `_get_*` 메서드를 먼저 확인합니다.
