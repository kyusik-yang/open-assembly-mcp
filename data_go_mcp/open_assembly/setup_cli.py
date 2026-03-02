"""Interactive setup wizard for open-assembly-mcp.

Run with: uvx open-assembly-mcp --setup
Or:       python -m data_go_mcp.open_assembly.setup_cli
"""

import json
import os
import platform
import sys
from pathlib import Path


# ── ANSI colors (disabled automatically on Windows without ANSI support) ──────

def _ansi(code: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def bold(t: str)  -> str: return _ansi("1", t)
def cyan(t: str)  -> str: return _ansi("96", t)
def green(t: str) -> str: return _ansi("92", t)
def yellow(t: str)-> str: return _ansi("93", t)
def dim(t: str)   -> str: return _ansi("2", t)


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
            print(f"  {yellow('!')} Could not parse existing config — a new one will be created.")
    return {}


def _write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Main wizard ───────────────────────────────────────────────────────────────

def run_setup() -> None:
    print()
    print(cyan("  ┌─────────────────────────────────────────────────────┐"))
    print(cyan("  │") + bold("        open-assembly-mcp  ·  Setup                 ") + cyan("│"))
    print(cyan("  │") + dim("        Korean National Assembly  MCP Server         ") + cyan("│"))
    print(cyan("  └─────────────────────────────────────────────────────┘"))
    print()

    # ── Step 1: API key ───────────────────────────────────────────────────────

    print(bold("  [1/3]  API Key"))
    print()
    print(f"  To use this server, you need a free API key from:")
    print(f"  이 서버를 사용하려면 무료 API 키가 필요합니다:")
    print()
    print(f"    {cyan('https://open.assembly.go.kr')}")
    print(f"    {dim('Sign up  →  마이페이지  →  API 키 발급  (approx. 2 min)')}")
    print()
    print(f"  {dim('For academic research access issues:  kyusik.yang@nyu.edu')}")
    print(f"  {dim('학술 연구 목적 이용 문의:              kyusik.yang@nyu.edu')}")
    print()

    existing_key = os.getenv("ASSEMBLY_API_KEY", "")
    if existing_key:
        print(f"  {green('✔')} Found ASSEMBLY_API_KEY in environment  ({existing_key[:6]}···)")
        use_existing = input("    Use this key? [Y/n]  ").strip().lower()
        api_key = existing_key if use_existing in ("", "y", "yes") else ""
    else:
        api_key = ""

    if not api_key:
        api_key = input("  Enter API key:  ").strip()

    if not api_key:
        print(f"\n  {yellow('!')} No key provided. Exiting.")
        sys.exit(1)

    # ── Step 2: Validate ──────────────────────────────────────────────────────

    print()
    print(bold("  [2/3]  Validating key  /  키 검증 중..."))
    print()

    if _test_api_key(api_key):
        print(f"  {green('✔')} Key is valid.  /  키가 유효합니다.")
    else:
        print(f"  {yellow('!')} Could not verify the key (network error or invalid key).")
        print(f"      키를 확인할 수 없습니다 (네트워크 오류 또는 잘못된 키).")
        proceed = input("    Continue anyway? [y/N]  ").strip().lower()
        if proceed not in ("y", "yes"):
            sys.exit(1)

    # ── Step 3: Write Claude Desktop config ───────────────────────────────────

    print()
    print(bold("  [3/3]  Configuring Claude Desktop"))
    print()

    config_path = _claude_desktop_config_path()
    print(f"  Config  {dim(str(config_path))}")
    print()

    config = _read_config(config_path)
    config.setdefault("mcpServers", {})

    if "open-assembly" in config["mcpServers"]:
        print(f"  {yellow('!')} An existing 'open-assembly' entry was found.")
        overwrite = input("    Overwrite? [Y/n]  ").strip().lower()
        if overwrite not in ("", "y", "yes"):
            print(f"\n  {dim('Skipped. Exiting.')}")
            sys.exit(0)

    config["mcpServers"]["open-assembly"] = {
        "command": "uvx",
        "args": ["open-assembly-mcp@latest"],
        "env": {"ASSEMBLY_API_KEY": api_key},
    }

    _write_config(config_path, config)

    # ── Done ──────────────────────────────────────────────────────────────────

    print()
    print(cyan("  ┌─────────────────────────────────────────────────────┐"))
    print(cyan("  │") + green(bold("  ✔  Setup complete!  ·  설정이 완료되었습니다.        ")) + cyan("│"))
    print(cyan("  └─────────────────────────────────────────────────────┘"))
    print()
    print(bold("  Next steps  /  다음 단계"))
    print()
    print(f"  1.  Restart Claude Desktop  {dim('/ Claude Desktop 재시작')}")
    print(f"  2.  Open a new conversation and look for the {bold('tools icon')}")
    print(f"      {dim('새 대화창을 열고 도구 아이콘 (망치)을 확인하세요')}")
    print(f"  3.  Try:  {cyan(repr('List AI-related bills from the 22nd Assembly'))}")
    print(f"      또는:  {cyan(repr('22대 국회 AI 관련 법안 목록 알려줘'))}")
    print()
