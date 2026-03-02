# open-assembly-mcp

[![PyPI](https://img.shields.io/pypi/v/open-assembly-mcp)](https://pypi.org/project/open-assembly-mcp/)
[![GitHub](https://img.shields.io/badge/github-open--assembly--mcp-blue.svg?style=flat&logo=github)](https://github.com/kyusik-yang/open-assembly-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-30%20passed-brightgreen)](tests/)
[![한국어](https://img.shields.io/badge/docs-한국어-blue)](README.ko.md)

**MCP server for the Korean National Assembly Open API** ([열린국회정보](https://open.assembly.go.kr)) — query bills, members, vote results, committee composition, and per-member vote records directly from Claude or any MCP-compatible AI client.

---

## Quick Start

**Step 1.** Get a free API key at [open.assembly.go.kr](https://open.assembly.go.kr)
→ Sign up → 마이페이지 → API 키 발급

**Step 2.** Run the setup wizard:

```bash
uvx open-assembly-mcp --setup
```

It prompts for your key, validates it, and writes the Claude Desktop config automatically.

**Step 3.** Restart Claude Desktop — the Assembly tools are ready.

---

## Usage Examples

Once connected, ask Claude in natural language (Korean or English):

```
22대 국회에서 발의된 AI 관련 법률안을 찾아줘
```
```
반도체특별법의 표결 결과와 공동발의자 명단을 알려줘
```
```
Find all housing-related bills in the 22nd Assembly that passed,
and list their lead proposers with party affiliation.
```
```
Which members of the 법제사법위원회 proposed the most bills in the 22nd Assembly?
```
```
Did any 더불어민주당 members vote against 국민투표법 개정안?
```

Claude chains the tools automatically and returns a structured summary.

---

## Available Tools

All tools return `total_count` and `has_more` for transparent pagination.
**Coverage**: 16th–22nd National Assembly (2000–present). Member-sponsored bills only.

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

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

The Korean National Assembly's [열린국회정보 API](https://open.assembly.go.kr) provides rich legislative data — every member-sponsored bill since 2000, full member rosters, plenary vote tallies, committee review timelines, and co-sponsor networks. The data is invaluable for political science research, but the traditional retrieval workflow is slow:

```
Traditional: search site manually → copy data → clean → load into Python/R
             → hours of overhead per research question

With MCP:    ask Claude in one sentence → tools chain automatically → results in seconds
```

**Concrete research use cases:**

| Task | Tools used |
|---|---|
| Co-sponsorship network for a policy domain | `search_bills` + `get_bill_proposers` |
| Party-line discipline on a specific vote | `get_member_votes` (filter by party) |
| Full legislative career of a single member | `search_bills` (proposer filter) |
| Committee composition by party | `get_committee_members` |
| Bill timeline from filing to promulgation | `get_bill_review` + `get_bill_detail` |
| Cross-party voting coalitions | `get_vote_results` + `get_member_votes` |

---

## Local Development

```bash
git clone https://github.com/kyusik-yang/open-assembly-mcp.git
cd open-assembly-mcp

cp .env.example .env        # add ASSEMBLY_API_KEY=your-key

uv sync --group dev
uv run pytest tests/ -v
```

```bash
# Run the server locally
ASSEMBLY_API_KEY=your-key uv run python -m data_go_mcp.open_assembly.server
```

---

## Changelog

### v0.2.2 (2026-03)
- `--setup` wizard: bilingual prompts (EN/KR), academic contact info

### v0.2.1 (2026-03)
- Added `--setup` wizard: interactive installer that auto-configures Claude Desktop

### v0.2.0 (2026-03)
- Added `get_member_votes` — per-member roll-call records for any bill
- All tools now return `total_count` and `has_more` for transparent pagination
- Added `propose_dt_from` / `propose_dt_to` date filter to `search_bills`
- Extended coverage to 16th and 17th Assemblies

### v0.1.0 (2026-02)
- Initial release

---

## License

Apache 2.0. See [LICENSE](LICENSE).

> This project was built following the architecture of [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers). The server structure, packaging conventions, and API client pattern are adapted from that project under the Apache 2.0 license.

*Not affiliated with or endorsed by the Korean National Assembly or open.assembly.go.kr.*

---

*Built with [Claude Code](https://claude.ai/code) — because the best way to make an AI tool for querying a legislature is to have an AI write it.*
