"""Interactive setup wizard for open-assembly-mcp.

Run with: uvx open-assembly-mcp --setup
Or:       python -m data_go_mcp.open_assembly.setup_cli
"""

import json
import os
import platform
import sys
from pathlib import Path


# ── ANSI helpers (auto-disabled when not a TTY) ──────────────────────────────

_COLOR = sys.stdout.isatty()

def _ansi(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text

def bold(t: str)   -> str: return _ansi("1", t)
def dim(t: str)    -> str: return _ansi("2", t)
def italic(t: str) -> str: return _ansi("3", t)
def cyan(t: str)   -> str: return _ansi("96", t)
def green(t: str)  -> str: return _ansi("92", t)
def yellow(t: str) -> str: return _ansi("93", t)
def red(t: str)    -> str: return _ansi("91", t)

def _rgb(r: int, g: int, b: int, text: str) -> str:
    """True-color (24-bit) foreground."""
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m" if _COLOR else text

def _bold_rgb(r: int, g: int, b: int, text: str) -> str:
    return f"\033[1;38;2;{r};{g};{b}m{text}\033[0m" if _COLOR else text


# ── Gradient banner ──────────────────────────────────────────────────────────

_BANNER_LINES = [
    r"   ___                      _                           _     _       ",
    r"  / _ \ _ __   ___ _ __    / \   ___ ___  ___ _ __ ___ | |__ | |_   _ ",
    r" | | | | '_ \ / _ \ '_ \  / _ \ / __/ __|/ _ \ '_ ` _ \| '_ \| | | | |",
    r" | |_| | |_) |  __/ | | |/ ___ \\__ \__ \  __/ | | | | | |_) | | |_| |",
    r"  \___/| .__/ \___|_| |_/_/   \_\___/___/\___|_| |_| |_|_.__/|_|\__, |",
    r"       |_|                                                       |___/ ",
]

# Gradient: teal → cyan → blue
_GRADIENT = [
    (0, 210, 190),
    (0, 195, 210),
    (30, 180, 225),
    (60, 165, 235),
    (90, 150, 240),
    (110, 140, 245),
]


def _print_banner() -> None:
    """Render the ASCII banner with a vertical color gradient."""
    print()
    for i, line in enumerate(_BANNER_LINES):
        r, g, b = _GRADIENT[i % len(_GRADIENT)]
        print(_bold_rgb(r, g, b, line))
    print()
    print(dim("  ─────────────────────────────────────────────────────────────────────"))
    print(
        f"  {_bold_rgb(0, 210, 190, 'open-assembly-mcp')}"
        f"  {dim('·')}  "
        f"{dim('Korean National Assembly MCP Server')}"
    )
    print(dim("  ─────────────────────────────────────────────────────────────────────"))
    print()


# ── Step header ──────────────────────────────────────────────────────────────

def _step(num: int, total: int, title: str, subtitle: str = "") -> None:
    label = _bold_rgb(0, 210, 190, f"  [{num}/{total}]")
    print(f"{label}  {bold(title)}")
    if subtitle:
        print(f"        {dim(subtitle)}")
    print()


# ── Config file paths ────────────────────────────────────────────────────────

def _claude_desktop_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


# ── API key validation ───────────────────────────────────────────────────────

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


# ── Config read/write ────────────────────────────────────────────────────────

def _read_config(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {yellow('⚠')} Could not parse existing config — a new one will be created.")
    return {}


def _write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Validation animation ─────────────────────────────────────────────────────

def _dots_print(msg: str) -> None:
    sys.stdout.write(f"  {msg}")
    sys.stdout.flush()
    try:
        import time
        for _ in range(3):
            time.sleep(0.25)
            sys.stdout.write(".")
            sys.stdout.flush()
    except Exception:
        sys.stdout.write("...")
    print()


# ── Main wizard ──────────────────────────────────────────────────────────────

def run_setup() -> None:
    _print_banner()

    # ── Step 1: API key ──────────────────────────────────────────────────────

    _step(1, 3, "API Key", "열린국회정보 API 키 입력")

    print(f"  Obtain a free API key from the National Assembly Open API portal.")
    print(f"  {dim('국회 열린국회정보 포털에서 무료 API 키를 발급받으세요.')}")
    print()
    print(f"    → {_bold_rgb(0, 210, 190, 'https://open.assembly.go.kr')}")
    print(f"      {dim('Sign up  →  마이페이지  →  인증키 신청/관리  (~2 min)')}")
    print()
    print(f"  {dim('Research access inquiries / 학술 연구 이용 문의')}")
    print(f"  {dim('kyusik.yang@nyu.edu')}")
    print()

    existing_key = os.getenv("ASSEMBLY_API_KEY", "")
    if existing_key:
        masked = existing_key[:6] + "···" + existing_key[-4:] if len(existing_key) > 10 else existing_key[:6] + "···"
        print(f"  {green('✔')} Detected ASSEMBLY_API_KEY in environment  {dim(f'({masked})')}")
        use_existing = input(f"  {bold('Use this key?')} [Y/n]  ").strip().lower()
        api_key = existing_key if use_existing in ("", "y", "yes") else ""
    else:
        api_key = ""

    if not api_key:
        api_key = input(f"  {bold('Paste your API key:')}  ").strip()

    if not api_key:
        print(f"\n  {yellow('⚠')} No key provided — exiting.")
        sys.exit(1)

    # ── Step 2: Validate ─────────────────────────────────────────────────────

    print()
    _step(2, 3, "Validate", "키 유효성 검증")

    _dots_print("Contacting open.assembly.go.kr")
    print()

    if _test_api_key(api_key):
        print(f"  {green('✔')} Key validated successfully.")
        print(f"    {dim('API 키가 정상적으로 확인되었습니다.')}")
    else:
        print(f"  {yellow('⚠')} Validation failed (network error or invalid key).")
        print(f"    {dim('키를 확인할 수 없습니다 — 네트워크 오류 또는 잘못된 키.')}")
        proceed = input(f"  {bold('Continue anyway?')} [y/N]  ").strip().lower()
        if proceed not in ("y", "yes"):
            sys.exit(1)

    # ── Step 3: Write Claude Desktop config ──────────────────────────────────

    print()
    _step(3, 3, "Configure Claude Desktop", "Claude Desktop 설정 파일에 기록")

    config_path = _claude_desktop_config_path()
    print(f"  Target  {dim(str(config_path))}")
    print()

    config = _read_config(config_path)
    config.setdefault("mcpServers", {})

    if "open-assembly" in config["mcpServers"]:
        print(f"  {yellow('⚠')} Existing {bold('open-assembly')} entry found.")
        overwrite = input(f"  {bold('Overwrite?')} [Y/n]  ").strip().lower()
        if overwrite not in ("", "y", "yes"):
            print(f"\n  {dim('Cancelled — no changes written.')}")
            sys.exit(0)

    config["mcpServers"]["open-assembly"] = {
        "command": "uvx",
        "args": ["open-assembly-mcp@latest"],
        "env": {"ASSEMBLY_API_KEY": api_key},
    }

    _write_config(config_path, config)
    print(f"  {green('✔')} Config written.")
    print(f"    {dim('설정 파일에 기록되었습니다.')}")

    # ── Done ─────────────────────────────────────────────────────────────────

    print()
    print(dim("  ─────────────────────────────────────────────────────────────────────"))
    print(f"  {_bold_rgb(0, 210, 190, '✔  Setup complete')}  {dim('·')}  {dim('설정이 완료되었습니다')}")
    print(dim("  ─────────────────────────────────────────────────────────────────────"))
    print()
    print(f"  {bold('Next steps')}")
    print()
    print(f"  {_bold_rgb(0, 210, 190, '1.')}  Restart Claude Desktop      {dim('Claude Desktop을 재시작하세요')}")
    print(f"  {_bold_rgb(0, 210, 190, '2.')}  Look for the {bold('🔨 tools icon')}   {dim('도구 아이콘이 표시되는지 확인하세요')}")
    print(f"  {_bold_rgb(0, 210, 190, '3.')}  Try a query:                 {dim('아래 예시를 시도해보세요')}")
    print()
    print(f"     {italic(cyan('22대 국회에서 발의된 AI 관련 법률안을 찾아줘'))}")
    print(f"     {italic(cyan('Find all housing-related bills in the 22nd Assembly'))}")
    print()
