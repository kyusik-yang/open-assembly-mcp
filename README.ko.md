# open-assembly-mcp

[![PyPI](https://img.shields.io/pypi/v/open-assembly-mcp)](https://pypi.org/project/open-assembly-mcp/)
[![GitHub](https://img.shields.io/badge/github-open--assembly--mcp-blue.svg?style=flat&logo=github)](https://github.com/kyusik-yang/open-assembly-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![English](https://img.shields.io/badge/docs-English-blue)](README.md)

**열린국회정보 API용 MCP 서버** — Claude에서 법률안, 의원 정보, 표결 결과, 위원회 구성, 개인별 표결 기록을 직접 조회할 수 있습니다.

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

Claude에게 자연어로 질문하면 됩니다:

```
22대 국회에서 발의된 AI 관련 법률안을 찾아줘
```
```
반도체특별법의 표결 결과와 공동발의자 명단을 알려줘
```
```
법제사법위원회 소속 의원 명단을 가져오고, 22대에서 해당 의원들이
대표발의한 법률안 수를 각각 세어줘
```
```
국민투표법 개정안 표결에서 더불어민주당 의원 중 반대표를 던진 사람이 있었나?
```
```
22대 국회 주거 관련 법안 중 가결된 것만 추려서 대표발의자 정당과 함께 정리해줘
```

Claude가 내부적으로 도구들을 연결해서 결과를 돌려줍니다.

---

## 제공 도구

모든 도구는 `total_count`(전체 결과 수)와 `has_more`(다음 페이지 존재 여부)를 함께 반환합니다.

**도구별 커버리지** (상세 검증은 향후 릴리즈에서 업데이트 예정):

| 도구 | 권장 범위 | 비고 |
|---|---|---|
| `search_bills` | 16~22대 | 의원 발의안 전용 (정부제출안 제외) |
| `get_bill_detail` | 16~22대 | |
| `get_bill_review` | 16~22대 | |
| `get_member_info` | 16~22대 | |
| `get_committee_members` | 16~22대 | |
| `get_vote_results` | 19~22대 권장 | 전자 표결 기록은 19대 이전 희소 |
| `get_member_votes` | 18~22대 권장 | 개인별 표결 데이터는 18대 이후부터 안정적 |
| `get_bill_proposers` | 16~22대 | 대수 필터 없음, 의안ID로 직접 조회 |

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
| 특정 표결의 정당 기율 분석 | `get_member_votes` (정당 필터) |
| 의원 개인의 입법 활동 전체 | `search_bills` (발의자 필터) |
| 정당별 위원회 구성 현황 | `get_committee_members` |
| 법안 발의부터 공포까지 타임라인 | `get_bill_review` + `get_bill_detail` |
| 초당적 표결 연합 분석 | `get_vote_results` + `get_member_votes` |

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
