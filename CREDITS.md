# Credits and Acknowledgments

## hollobit/assembly-api-mcp

**Author**: hollobit  
**Repository**: https://github.com/hollobit/assembly-api-mcp  
**License**: MIT  
**Permission**: Explicit permission obtained from the author.

### What was adapted

The following ideas and patterns were adopted from hollobit/assembly-api-mcp:

| Feature | Location in this project | Notes |
|---------|--------------------------|-------|
| `query_assembly` tool concept — universal fallback to call any API endpoint directly | `server.py: query_assembly` | Adapted pattern; Python implementation |
| `discover_apis` tool concept — keyword search across registered endpoints | `server.py: discover_apis` | Adapted pattern; Python implementation |
| Endpoint registry structure — organizing API codes with metadata | `registry.py: ENDPOINT_REGISTRY` | Structure inspired; all codes independently verified |
| Raw JSON fallback when non-standard response formats are encountered | `client.py: query_endpoint` | Implementation differs; same concept |

### What was not adapted

- All 11 API endpoint codes in `registry.py` were independently discovered and tested
  against open.assembly.go.kr before hollobit's project was reviewed.
- All 12 dedicated MCP tools (`search_bills`, `get_member_votes`, etc.) and their
  parameter designs predate any review of hollobit's project.
- The Python/FastMCP architecture, `AssemblyAPIClient`, `_parse_response`,
  `ALLNAMEMBER`-based historical data handling, and all test code are original.

---

## Koomook/data-go-mcp-servers

**Repository**: https://github.com/Koomook/data-go-mcp-servers  
**License**: Apache 2.0

The original project structure, packaging conventions, and FastMCP server pattern
were adapted from this project. See `LICENSE` for full terms.
