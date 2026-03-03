# open-assembly-mcp

[![PyPI](https://img.shields.io/pypi/v/open-assembly-mcp)](https://pypi.org/project/open-assembly-mcp/)
[![GitHub](https://img.shields.io/badge/github-open--assembly--mcp-blue.svg?style=flat&logo=github)](https://github.com/kyusik-yang/open-assembly-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![English](https://img.shields.io/badge/docs-English-blue)](README.md)

**열린국회정보 API용 MCP 서버** — Claude에서 법률안, 의원 정보, 표결 결과, 위원회 구성, 계류의안, 본회의 부의안건, 개인별 표결 기록을 직접 조회할 수 있습니다.

---

## 빠른 시작

**사전 준비:** [Claude Desktop](https://claude.ai/download)이 설치되어 있어야 합니다.

**Step 1.** [open.assembly.go.kr](https://open.assembly.go.kr)에서 무료 API 키 발급
→ 회원가입 → 마이페이지 → API 키 발급

**Step 2.** 설치 마법사 실행:

```bash
uvx open-assembly-mcp --setup
```

API 키를 입력하면 검증 후 Claude Desktop 설정 파일을 자동으로 작성합니다.

**Step 3.** Claude Desktop 재시작 — 바로 사용 가능합니다.

---

## 사용 예시

Claude에게 자연어로 질문하면 됩니다. Claude가 내부적으로 도구들을 순서대로 연결합니다.

---

### 시나리오 1 - 정책 도메인 법안 탐색

> **"22대 국회에서 발의된 인공지능 관련 법률안 목록을 찾아줘. 처리 결과별로 요약하고, 통과된 법안은 공동발의자도 알려줘."**

Claude 호출 순서:
1. `search_bills(age="22", bill_name="인공지능", page_size=50)` → 47건 발견
2. 통과 법안 각각: `get_bill_proposers(bill_id="PRC_...")` → 공동발의자 목록

**출력 예시:**
```
인공지능 관련 법률안 47건 (22대)

처리 결과:
  원안가결  3건
  수정가결  1건
  폐기     28건
  계류 중  15건

통과된 법안 공동발의자:
  인공지능산업육성법안 (원안가결)
    홍길동 (민주당), 김철수 (민주당) ... 총 22명
```

---

### 시나리오 2 - 법안 입법 여정 추적

> **"반도체특별법 (의안번호 2216983)의 입법 여정을 처음부터 끝까지 보여줘."**

Claude 호출 순서:
1. `get_bill_review(age="22", bill_no="2216983")` → 위원회 + 본회의 타임라인
2. `get_bill_committee_review(bill_id="PRC_...")` → 위원회 심사 회의 일정
3. `get_bill_detail(bill_no="2216983")` → 상세 정보 + 원문 링크

**출력 예시:**
```
반도체산업경쟁력강화특별법안
발의일: 2023-11-08  대표발의자: 이OO  소관위: 산자위

위원회 심사:
  2023-11-15  산자위 상정
  2023-12-07  산자위 의결 (원안가결)

본회의:
  2024-01-09  찬성 180 / 반대 92 / 기권 5  → 원안가결
  2024-01-30  공포 (법률 제19XXX호)

원문: https://likms.assembly.go.kr/bill/...
```

---

### 시나리오 3 - 정당별 표결 분석

> **"국민투표법 개정안 표결에서 각 정당 의원들은 어떻게 투표했나? 당론을 이탈한 의원이 있었나?"**

Claude 호출 순서:
1. `get_vote_results(age="22", bill_name="국민투표법")` → 의안 확인 + 집계 + BILL_ID 획득
2. `get_member_votes(bill_id="PRC_...", age="22")` → 의원별 표결 300행

**출력 예시:**
```
국민투표법 일부개정법률안
전체: 찬성 180 / 반대 110 / 기권 7

정당별 표결:
  더불어민주당  찬성 163 / 반대 0 / 기권 3
  국민의힘     찬성   0 / 반대 107 / 기권 2
  조국혁신당   찬성  12 / 반대 0 / 기권 0

당론 이탈 (기권):
  민주당: 김OO (서울OO), 이OO (경기OO)
  국민의힘: 최OO (대구OO)
```

---

### 시나리오 4 - 의원 입법 활동 분석

> **"이준석 의원 (22대)의 입법 활동을 요약해줘. 발의 법안과 최근 표결 성향을 보여줘."**

Claude 호출 순서:
1. `get_member_info(age="22", name="이준석")` → 정당, 지역구, 위원회
2. `search_bills(age="22", proposer="이준석", page_size=100)` → 전체 발의 법안
3. `get_vote_results(age="22", page_size=20)` → 최근 표결 법안 목록
4. 각 법안: `get_member_votes(bill_id=..., age="22", member_name="이준석")`

---

### 시나리오 5 - 계류의안 현황 파악

> **"과학기술정보방송통신위원회에 현재 계류 중인 법안은 몇 개야? AI·반도체 관련은 따로 봐줘."**

Claude 호출:
1. `get_pending_bills(age="22", committee="과학기술정보방송통신위원회", page_size=100)` → 127건

**출력 예시:**
```
과기위 계류의안: 총 127건 (2025-03 기준)

AI·반도체 관련 (키워드 필터):
  인공지능 관련      12건
  반도체·소부장 관련  8건
  기타 디지털       107건

가장 오래된 계류 법안:
  2022-07-05 발의 — OOO법 일부개정안 (이OO)
```

---

### 시나리오 6 - 다음 본회의 상정 안건 확인

> **"다음 본회의에 상정될 법안 목록을 알려줘."**

Claude 호출:
1. `get_plenary_agenda(age="22", page_size=30)` → 상정 예정 안건

---

## 제공 도구

모든 도구는 `total_count`(전체 결과 수)와 `has_more`(다음 페이지 여부)를 함께 반환합니다.

### 빠른 참조

| 도구 | 핵심 파라미터 | 반환 |
|---|---|---|
| `search_bills` | `age`, `bill_name`, `proposer`, `proc_result`, `committee`, `propose_dt_from/to` | `bills[]`, `total_count`, `has_more` |
| `get_bill_detail` | `bill_no` (BILL_NO) | `bill{}` |
| `get_bill_review` | `age`, `bill_no`, `committee` | `reviews[]` |
| `get_bill_proposers` | `bill_id` (BILL_ID) | `proposers[]` |
| `get_bill_committee_review` | `bill_id` (BILL_ID) | `meetings[]` |
| `get_member_info` | `age`, `name`, `party`, `district`, `committee` | `members[]` |
| `get_committee_members` | `age`, `committee` | `members[]` |
| `get_vote_results` | `age`, `bill_no`, `bill_name` | `votes[]` — `YES_TCNT`, `NO_TCNT`, `BLANK_TCNT`, `BILL_ID` 포함 |
| `get_member_votes` | `bill_id` (BILL_ID), `age`, `member_name`, `party`, `vote_result` | `votes[]` — `RESULT_VOTE_MOD` 포함 |
| `get_pending_bills` | `age`, `bill_name`, `committee`, `proposer` | `bills[]`, `total_count`, `has_more` |
| `get_plenary_agenda` | `age`, `session` | `agenda_items[]`, `total_count`, `has_more` |

> **BILL_ID vs BILL_NO 구분** — 여러 도구가 `BILL_NO`(7자리 공개 번호, 예: `2216983`)가 아닌
> `BILL_ID`(내부 ID, 예: `PRC_...`)를 필요로 합니다. 두 값 모두 `search_bills`와
> `get_pending_bills` 결과에 포함됩니다.
> `BILL_ID` 필요 도구: `get_bill_proposers`, `get_member_votes`, `get_bill_committee_review`.

### 대수별 커버리지

| 도구 | 권장 범위 | 비고 |
|---|---|---|
| `search_bills` | 16~22대 | 의원 발의안 전용 (정부제출안 제외) |
| `get_bill_detail` | 16~22대 | |
| `get_bill_review` | 16~22대 | |
| `get_member_info` | 16~22대 | |
| `get_committee_members` | 16~22대 | |
| `get_vote_results` | 19~22대 권장 | 전자 표결 기록은 19대 이전 희소 |
| `get_member_votes` | 18~22대 권장 | 개인별 표결 데이터는 18대 이후부터 안정적; 기본 page_size=300으로 전체 의원 1회 조회 |
| `get_bill_proposers` | 16~22대 | |
| `get_pending_bills` | 22대 권장 | 미처리 계류의안; 22대 기준 약 8,900건 |
| `get_plenary_agenda` | 22대 권장 | 본회의 상정 예정 안건 목록 |
| `get_bill_committee_review` | 16~22대 | 특정 의안의 위원회 심사 회의정보 (BILL_ID 필요) |

**Open API 미제공 항목**: 회의록, 청원, 법안 전문
(`get_bill_detail` → `LINK_URL`에서 공식 의안 페이지 확인 가능).

---

## 업데이트

`uvx`는 패키지를 로컬에 캐시합니다. 이전 버전이 설치되어 있다면 아래 명령으로 강제 재설치하세요:

```bash
uvx --reinstall open-assembly-mcp --setup
```

Claude Desktop config에 `open-assembly-mcp@latest`로 설정해두면 항상 최신 버전으로 실행됩니다.

---

## 수동 설정 (--setup 대신)

Claude Desktop 설정 파일 직접 편집:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "open-assembly": {
      "command": "uvx",
      "args": ["open-assembly-mcp@latest"],
      "env": {
        "ASSEMBLY_API_KEY": "발급받은_키_입력"
      }
    }
  }
}
```

저장 후 Claude Desktop 재시작.

---

## Claude Code (CLI) 설정

```bash
claude mcp add open-assembly \
  --command uvx \
  --args "open-assembly-mcp@latest" \
  --env "ASSEMBLY_API_KEY=발급받은_키_입력"
```

---

## 왜 만들었나

열린국회정보 API는 2000년 이후 모든 의원 발의 법률안, 의원 명단, 본회의 표결 집계, 위원회 심사 내역, 공동발의 네트워크를 담고 있습니다. 정치학 연구에 매우 유용한 데이터지만, 기존 수집 방식은 번거롭습니다:

```
기존 방식: 사이트 수동 검색 → 데이터 복사/정제 → Python/R 로드
           → 연구 질문 하나당 수 시간 소요

MCP 방식: Claude에게 한 문장으로 질문 → 도구 자동 연결 → 수 초 내 결과
```

**구체적인 연구 활용 사례:**

| 연구 과제 | 사용 도구 |
|---|---|
| 특정 정책 도메인 공동발의 네트워크 | `search_bills` + `get_bill_proposers` |
| 특정 표결의 정당 기율 분석 | `get_vote_results` + `get_member_votes` (정당 필터) |
| 초당적 표결 연합 분석 | `get_vote_results` + `get_member_votes` |
| 의원 개인의 입법 활동 전체 | `search_bills` (발의자 필터) + `get_member_votes` |
| 정당별 위원회 구성 현황 | `get_committee_members` |
| 법안 발의부터 공포까지 타임라인 | `get_bill_review` + `get_bill_committee_review` + `get_bill_detail` |
| 특정 정책 영역 현재 계류의안 파악 | `get_pending_bills` (위원회/키워드 필터) |
| 다음 본회의 표결 예정 법안 | `get_plenary_agenda` |
| 가결 법안의 연대 구축 분석 | `get_bill_proposers` + `get_member_votes` |

---

## 로컬 개발

```bash
git clone https://github.com/kyusik-yang/open-assembly-mcp.git
cd open-assembly-mcp

cp .env.example .env        # ASSEMBLY_API_KEY=발급받은_키 추가

uv sync --group dev
uv run pytest tests/ -v
```

---

## 변경 이력

### v0.2.5 (2026-03)
- 신규 도구 3개: `get_pending_bills` (계류의안), `get_plenary_agenda` (본회의부의안건), `get_bill_committee_review` (위원회 심사 회의정보)
- `get_member_votes` 기본 page_size 50 → 300으로 수정 (본회의 전체 의원 1회 조회)
- docstring 개선: `get_vote_results` 오류 설명 수정, 모든 도구에 페이지네이션 안내 추가

### v0.2.4 (2026-03)
- `--setup` 마법사: ASCII 아트 배너 + 그라디언트 색상, 애니메이션 검증, 전문적 이중언어 프롬프트

### v0.2.1 (2026-03)
- `--setup` 마법사 추가: Claude Desktop 자동 설정

### v0.2.0 (2026-03)
- `get_member_votes` 추가 — 의안별 의원 개인 표결 기록
- 모든 도구에 `total_count`, `has_more` 추가
- `search_bills` 발의일 기간 필터 추가
- 16~17대 국회 지원 추가

### v0.1.0 (2026-02)
- 최초 릴리즈

---

## 라이선스

Apache 2.0. [LICENSE](LICENSE) 참조.

> 이 프로젝트는 [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers)의 구조와 패턴을 참고해 제작했습니다.

*이 프로젝트는 대한민국 국회 또는 open.assembly.go.kr과 공식적인 관계가 없습니다.*
