"""Interactive setup wizard for open-assembly-mcp.

Run with: uvx open-assembly-mcp --setup
Or:       python -m data_go_mcp.open_assembly.setup_cli
"""

import json
import os
import platform
import sys
from pathlib import Path


# ── Config file paths ─────────────────────────────────────────────────────────

def _claude_desktop_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


# ── API key validation ────────────────────────────────────────────────────────

def _test_api_key(key: str) -> bool:
    """Make a minimal API call to verify the key works."""
    try:
        import httpx
        r = httpx.get(
            "https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn",
            params={"KEY": key, "Type": "json", "AGE": "22", "pSize": "1"},
            timeout=10,
        )
        r.raise_for_status()
        body = r.json()
        head = body.get("nzmimeepazxkubdpn", [{}])[0].get("head", [{}])
        code = head[1].get("RESULT", {}).get("CODE", "") if len(head) > 1 else ""
        return code in ("INFO-000", "INFO-200")
    except Exception:
        return False


# ── Config read/write ─────────────────────────────────────────────────────────

def _read_config(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  Warning: could not parse existing config at {path}. Will create a new one.")
    return {}


def _write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Main wizard ───────────────────────────────────────────────────────────────

def run_setup() -> None:
    print()
    print("=" * 60)
    print("  open-assembly-mcp  --  Setup Wizard")
    print("  Korean National Assembly MCP Server")
    print("=" * 60)
    print()

    # Step 1: API key
    print("Step 1/3  Get your API key")
    print("  - Visit: https://open.assembly.go.kr")
    print("  - Sign up (무료 회원가입) → 마이페이지 → API 키 발급")
    print()

    existing_key = os.getenv("ASSEMBLY_API_KEY", "")
    if existing_key:
        print(f"  Found ASSEMBLY_API_KEY in environment ({existing_key[:6]}...)")
        use_existing = input("  Use this key? [Y/n] ").strip().lower()
        api_key = existing_key if use_existing in ("", "y", "yes") else ""
    else:
        api_key = ""

    if not api_key:
        api_key = input("  Paste your API key: ").strip()

    if not api_key:
        print("\n  No API key provided. Exiting.")
        sys.exit(1)

    # Step 2: Validate key
    print()
    print("Step 2/3  Validating key...")
    if _test_api_key(api_key):
        print("  Key is valid.")
    else:
        print("  Warning: could not verify the key (network issue or invalid key).")
        proceed = input("  Continue anyway? [y/N] ").strip().lower()
        if proceed not in ("y", "yes"):
            sys.exit(1)

    # Step 3: Write Claude Desktop config
    print()
    print("Step 3/3  Configure Claude Desktop")
    config_path = _claude_desktop_config_path()
    print(f"  Config file: {config_path}")

    config = _read_config(config_path)
    config.setdefault("mcpServers", {})

    if "open-assembly" in config["mcpServers"]:
        print("  'open-assembly' server already exists in config.")
        overwrite = input("  Overwrite? [Y/n] ").strip().lower()
        if overwrite not in ("", "y", "yes"):
            print("  Skipped. Exiting.")
            sys.exit(0)

    config["mcpServers"]["open-assembly"] = {
        "command": "uvx",
        "args": ["open-assembly-mcp@latest"],
        "env": {
            "ASSEMBLY_API_KEY": api_key,
        },
    }

    _write_config(config_path, config)

    print()
    print("=" * 60)
    print("  Setup complete!")
    print()
    print("  Next steps:")
    print("  1. Restart Claude Desktop")
    print("  2. Look for the hammer icon (tools) in a new conversation")
    print("  3. Try: '22대 국회에서 발의된 AI 관련 법안 목록 알려줘'")
    print("=" * 60)
    print()
