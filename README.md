# open-assembly-mcp

[![PyPI](https://img.shields.io/pypi/v/open-assembly-mcp)](https://pypi.org/project/open-assembly-mcp/)
[![GitHub](https://img.shields.io/badge/github-open--assembly--mcp-blue.svg?style=flat&logo=github)](https://github.com/kyusik-yang/open-assembly-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-30%20passed-brightgreen)](tests/)

**MCP server for the Korean National Assembly Open API** ([열린국회정보](https://open.assembly.go.kr)) — query bills, members, vote results, committee composition, and per-member vote records directly from Claude.

---

## Quick Start

**Step 1.** Get a free API key at [open.assembly.go.kr](https://open.assembly.go.kr) → 회원가입 → 마이페이지 → API 키 발급

**Step 2.** Run the setup wizard:

```bash
uvx open-assembly-mcp --setup
```

It asks for your key, validates it, and writes the Claude Desktop config automatically.

**Step 3.** Restart Claude Desktop — the Assembly tools are ready.

---

## Usage Examples

Once connected, ask Claude in natural language:

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
Find all housing-related bills in the 22nd assembly that passed, and list
their lead proposers with party affiliation.
```

Claude chains the tools automatically and returns a structured summary.

---

## Available Tools

All tools return `total_count` and `has_more` for transparent pagination.
**Coverage**: 16th–22nd Assembly (2000–present). Member-sponsored bills only.

| Tool | Description |
|---|---|
| `search_bills` | Search bills by assembly, keyword, proposer, committee, date range, or outcome |
| `get_bill_detail` | Full bill record including processing history and plenary result |
| `get_member_info` | Member profiles: party, district, committee, election type |
| `get_vote_results` | Plenary vote tallies per bill: yes / no / abstain counts |
| `get_member_votes` | Per-member roll-call records for a specific bill |
| `get_bill_proposers` | Lead and co-sponsor list for a bill |
| `get_bill_review` | Bill review timeline through committee and plenary stages |
| `get_committee_members` | Committee member roster |

**Not available via Open API**: transcripts, citizen petitions, bill full text
(use `get_bill_detail` → `LINK_URL` for the official bill page).

---

## Manual Config (alternative to --setup)

If you prefer to edit the config file directly:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "open-assembly": {
      "command": "uvx",
      "args": ["open-assembly-mcp@latest"],
      "env": {
        "ASSEMBLY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

## Claude Code Setup

```bash
claude mcp add open-assembly \
  --command uvx \
  --args "open-assembly-mcp@latest" \
  --env "ASSEMBLY_API_KEY=your-key-here"
```

---

## Why this exists

The Korean National Assembly's Open API contains rich legislative data — every bill since 2000, full member rosters, plenary vote tallies, co-sponsor networks — but the standard workflow is slow:

```
Traditional: visit site → search manually → copy data → clean → load into Python/R
             → hours of overhead per research question

With MCP:    ask Claude in one sentence → tools chain automatically → results in seconds
```

**Research use cases:**

| Task | Tools |
|---|---|
| Co-sponsorship network for a policy domain | `search_bills` + `get_bill_proposers` |
| Party-line discipline on a specific vote | `get_member_votes` (filter by party) |
| Legislative career of a single member | `search_bills` (proposer filter) |
| Committee composition by party | `get_committee_members` |
| Bill timeline from filing to promulgation | `get_bill_review` + `get_bill_detail` |

---

## Local Development

```bash
git clone https://github.com/kyusik-yang/open-assembly-mcp.git
cd open-assembly-mcp

cp .env.example .env        # add your ASSEMBLY_API_KEY

uv sync --group dev
uv run pytest tests/ -v
```

```bash
# Run server locally
ASSEMBLY_API_KEY=your-key uv run python -m data_go_mcp.open_assembly.server
```

---

## Changelog

### v0.2.1 (2026-03)
- Added `--setup` wizard: interactive install that auto-configures Claude Desktop

### v0.2.0 (2026-03)
- Added `get_member_votes` -- per-member roll-call records for any bill
- All tools now return `total_count` and `has_more` for transparent pagination
- Added date filter to `search_bills`
- Extended coverage to 16th and 17th Assemblies

### v0.1.0 (2026-02)
- Initial release

---

## License

Apache 2.0. See [LICENSE](LICENSE).

> This project was built following the architecture of [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers). The server structure, packaging conventions, and API client pattern are adapted from that project.

*This project is not affiliated with or endorsed by the Korean National Assembly.*

---

*Built with [Claude Code](https://claude.ai/code) — because the best way to make an AI tool for querying a legislature is to have an AI write it.*
