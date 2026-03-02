# open-assembly-mcp

[![GitHub](https://img.shields.io/badge/github-open--assembly--mcp-blue.svg?style=flat&logo=github)](https://github.com/kyusik-yang/open-assembly-mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-30%20passed-brightgreen)](tests/)

**MCP server for the Korean National Assembly Open API** ([열린국회정보](https://open.assembly.go.kr)) — query bills, members, vote results, committee composition, and bill proposers directly from Claude or any MCP-compatible AI client.

> **Acknowledgement**: This project was built following the architecture and conventions of [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers), an open-source collection of Korean public data MCP servers. The server structure, API client pattern, and packaging conventions are adapted from that project under the Apache 2.0 license.

---

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Why an Open Assembly MCP?](#why-an-open-assembly-mcp)
- [Available Tools](#available-tools)
- [Installation](#installation)
- [Claude Desktop Setup](#claude-desktop-setup)
- [Usage Examples](#usage-examples)
- [API Key](#api-key)
- [Local Development](#local-development)
- [License](#license)

---

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that lets AI assistants like Claude call external tools and APIs directly within a conversation. An MCP server exposes a set of typed functions ("tools") that the AI can invoke, receive structured results from, and reason over — without any copy-pasting or manual data retrieval.

---

## Why an Open Assembly MCP?

The Korean National Assembly's [열린국회정보 API](https://open.assembly.go.kr) contains rich legislative data: every bill filed since the 16th Assembly, full member rosters, plenary vote tallies, committee review timelines, and co-sponsor networks. This data is invaluable for political science research, but the traditional workflow is slow:

```
Traditional workflow
──────────────────────────────────────────────────────────────
1. Visit open.assembly.go.kr or the bill information system
2. Search manually, page through results
3. Download or copy data, clean it
4. Load into Python/R for analysis
5. Repeat for each sub-query (proposers, votes, committee...)
   → Hours of overhead per research question
```

```
With open-assembly-mcp
──────────────────────────────────────────────────────────────
"22대 국회에서 발의된 AI 관련 법률안 목록, 대표발의자 소속 정당,
 본회의 표결 결과까지 정리해줘"
   → Claude calls search_bills → get_bill_proposers → get_vote_results
   → Returns a structured summary in seconds
```

### Concrete research use cases

| Research task | Tools used |
|---|---|
| Map the co-sponsorship network for housing policy bills | `search_bills` + `get_bill_proposers` |
| Track which committee reviewed a bill and when | `get_bill_review` + `get_bill_detail` |
| Compare yes/no/abstain rates across parties on a specific bill | `get_vote_results` + `get_member_info` |
| Get individual member voting records to analyze party-line discipline | `get_member_votes` (filter by party or vote_result) |
| List all bills proposed by a specific member | `search_bills` (proposer filter) |
| Audit committee composition by party for a given assembly | `get_committee_members` |
| Identify bills that passed vs. were scrapped in a policy domain | `search_bills` (proc_result filter) |

### Why this matters for legislative research

- **Speed**: Multi-step queries that previously took hours of manual data collection take seconds.
- **Reproducibility**: Every query is a structured API call with explicit parameters — easy to document and re-run.
- **Chaining**: Claude can chain multiple tools in a single request, e.g., find a bill, get its proposers, look up each proposer's party and committee.
- **Iteration**: Natural language lets you refine queries without rewriting code — crucial during exploratory analysis.
- **Accessibility**: Researchers without strong programming backgrounds can access the same data as those who script API calls directly.

---

## Available Tools

### Available tools (endpoints verified February–March 2026)

All tools return `total_count` (total matching records) and `has_more` (whether additional pages exist) alongside results — giving Claude everything it needs to decide whether to paginate.

| Tool | Description | Endpoint |
|---|---|---|
| `search_bills` | Search member-sponsored bills by assembly, keyword, proposer, result, committee, or date range | `nzmimeepazxkubdpn` |
| `get_bill_detail` | Full bill record including processing history, committee schedule, and plenary result | `ALLBILL` |
| `get_member_info` | National Assembly member profiles: party, district, committee, election type | `nwvrqwxyaytdsfvhu` |
| `get_vote_results` | Plenary vote tallies by bill: yes / no / abstain / absent counts | `ncocpgfiaoituanbr` |
| `get_bill_review` | Bill review timeline through committee and plenary stages | `nwbpacrgavhjryiph` |
| `get_bill_proposers` | Lead and co-sponsor list for a bill (requires `BILL_ID` from `search_bills`) | `BILLINFOPPSR` |
| `get_member_votes` | Per-member yes/no/abstain vote records for a specific bill (requires `BILL_ID` + `age`) | `nojepdqqaweusdfbi` |
| `get_committee_members` | Committee member roster filtered by committee name | `nwvrqwxyaytdsfvhu` + filter |

**Coverage**: 16th–22nd Assembly (2000–present). Tools cover member-sponsored bills only; government-submitted bills are not available through the Open API.

**Unavailable via Open API**: committee and plenary transcripts ([likms.assembly.go.kr/record](https://likms.assembly.go.kr/record/)), citizen petitions ([petitions.assembly.go.kr](https://petitions.assembly.go.kr/)), and bill full text (use `get_bill_detail` → `LINK_URL`).

---

## Installation

### Using uvx (recommended — no install needed)

```bash
uvx data-go-mcp.open-assembly
```

### Using uv

```bash
uv pip install data-go-mcp.open-assembly
```

### Using pip

```bash
pip install data-go-mcp.open-assembly
```

---

## Claude Desktop Setup

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "open-assembly": {
      "command": "uvx",
      "args": ["data-go-mcp.open-assembly@latest"],
      "env": {
        "ASSEMBLY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop after saving. The Assembly tools will appear in the tool list.

---

## Usage Examples

Once connected, you can ask Claude questions like:

```
22대 국회에서 발의된 AI 관련 법률안을 찾아줘
```
```
더불어민주당 소속 의원 명단과 각각의 소속 위원회를 정리해줘
```
```
반도체특별법의 표결 결과와 공동발의자 명단을 알려줘
```
```
Find all housing-related bills in the 22nd assembly that passed, and list
their lead proposers with party affiliation.
```
```
법제사법위원회 소속 의원 명단을 가져오고, 22대에서 해당 의원들이
대표발의한 법률안 수를 각각 세어줘
```
```
국민투표법 개정안 표결에서 더불어민주당 의원 중 반대표를 던진 사람이 있었나?
```

Claude will call the appropriate tools, chain results, and return a structured summary.

---

## API Key

An API key for 열린국회정보 is **free**. Sign up at [open.assembly.go.kr](https://open.assembly.go.kr), navigate to **마이페이지 → API 키 발급**, and copy the key.

Set it as an environment variable:

```bash
export ASSEMBLY_API_KEY="your-key-here"
```

Or put it in a `.env` file (see `.env.example`):

```
ASSEMBLY_API_KEY=your-key-here
```

---

## Local Development

```bash
git clone https://github.com/kyusik-yang/open-assembly-mcp.git
cd open-assembly-mcp

cp .env.example .env
# Add your ASSEMBLY_API_KEY to .env

uv sync --dev
uv run pytest tests/ -v
```

### Running the server locally

```bash
ASSEMBLY_API_KEY=your-key uv run python -m data_go_mcp.open_assembly.server
```

Or point Claude Desktop at the local source:

```json
{
  "mcpServers": {
    "open-assembly-local": {
      "command": "/path/to/open-assembly-mcp/.venv/bin/python",
      "args": ["-m", "data_go_mcp.open_assembly.server"],
      "cwd": "/path/to/open-assembly-mcp",
      "env": {
        "ASSEMBLY_API_KEY": "your-key-here"
      }
    }
  }
}
```

### Project structure

```
open-assembly-mcp/
├── data_go_mcp/
│   └── open_assembly/
│       ├── client.py      # Async httpx client for 열린국회정보 API
│       └── server.py      # FastMCP server + tool definitions
├── tests/
│   ├── test_client.py     # Unit tests for API response parsing
│   └── test_server.py     # Integration-style tests for each tool
├── pyproject.toml
└── .env.example
```

---

## License

Apache 2.0. See [LICENSE](LICENSE).

This project was built following the architecture of [Koomook/data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers). The server structure, packaging conventions, and API client pattern are adapted from that project. Changes include: new API client targeting 열린국회정보 (open.assembly.go.kr), seven new tool definitions, endpoint discovery and verification for all confirmed endpoints, and tests.

---

*This project is not affiliated with or endorsed by the Korean National Assembly or open.assembly.go.kr. Please review the [열린국회정보 이용약관](https://open.assembly.go.kr) before use.*

---

*Built with [Claude Code](https://claude.ai/code) — because the best way to make an AI tool for querying parliament is to have an AI write it.*
