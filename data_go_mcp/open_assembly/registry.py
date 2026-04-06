"""Registry of verified Korean National Assembly Open API endpoint codes.

Provides structured metadata for known API endpoints to support the
discover_apis tool. Only codes that have been directly tested against
open.assembly.go.kr are listed here.

For the complete catalog of 276+ endpoints, visit:
  https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do

Registry structure and organization inspired by hollobit/assembly-api-mcp
(MIT License, https://github.com/hollobit/assembly-api-mcp).
"""

from typing import Optional

ENDPOINT_REGISTRY: dict[str, dict] = {

    # ================================================================
    # Bills / 의안
    # ================================================================

    "nzmimeepazxkubdpn": {
        "name": "국회의원 발의법률안",
        "name_en": "Member-Sponsored Bills",
        "category": "bills",
        "mcp_tool": "search_bills",
        "key_params": ["AGE", "BILL_NAME", "PROPOSER", "PROC_RESULT", "COMMITTEE"],
        "assembly_range": "16th-22nd",
        "notes": (
            "Primary entry point for bill queries. Member-initiated bills only; "
            "excludes government-submitted bills. Both BILL_NO and BILL_ID returned."
        ),
        "verified": True,
    },

    "ALLBILL": {
        "name": "의안정보 통합 API",
        "name_en": "Bill Information (Integrated)",
        "category": "bills",
        "mcp_tool": "get_bill_detail",
        "key_params": ["BILL_NO"],
        "assembly_range": "16th-22nd",
        "notes": (
            "Full bill metadata including LINK_URL to official bill page. "
            "Requires BILL_NO (7-digit public number), NOT BILL_ID."
        ),
        "verified": True,
    },

    "nwbpacrgavhjryiph": {
        "name": "의안 처리·심사정보",
        "name_en": "Bill Review and Processing Status",
        "category": "bills",
        "mcp_tool": "get_bill_review",
        "key_params": ["AGE", "BILL_NO", "COMMITTEE_NM"],
        "assembly_range": "16th-22nd",
        "notes": (
            "High-level legislative timeline: committee referral/decision dates "
            "and plenary outcome. Note: uses COMMITTEE_NM (not COMMITTEE) for filtering."
        ),
        "verified": True,
    },

    "BILLINFOPPSR": {
        "name": "의안 제안자정보",
        "name_en": "Bill Proposers (Co-Sponsors)",
        "category": "bills",
        "mcp_tool": "get_bill_proposers",
        "key_params": ["BILL_ID"],
        "assembly_range": "16th-22nd",
        "notes": (
            "All proposers: lead and co-sponsors, with name, party, and role. "
            "Requires BILL_ID (PRC_...), not BILL_NO. Essential for co-sponsorship network analysis."
        ),
        "verified": True,
    },

    "BILLJUDGECONF": {
        "name": "위원회 심사 회의정보",
        "name_en": "Bill Committee Review Meetings",
        "category": "bills",
        "mcp_tool": "get_bill_committee_review",
        "key_params": ["BILL_ID"],
        "assembly_range": "16th-22nd",
        "notes": (
            "Individual committee meeting records for a bill (one row per meeting). "
            "Requires BILL_ID (PRC_...). Use together with get_bill_review for full timeline."
        ),
        "verified": True,
    },

    "nwbqublzajtcqpdae": {
        "name": "계류의안",
        "name_en": "Pending Bills",
        "category": "bills",
        "mcp_tool": "get_pending_bills",
        "key_params": ["AGE", "BILL_NAME", "COMMITTEE", "PROPOSER"],
        "assembly_range": "22nd recommended",
        "notes": (
            "Bills currently awaiting committee or plenary action (~8,900 in 22nd Assembly). "
            "Excludes passed, rejected, or withdrawn bills."
        ),
        "verified": True,
    },

    "nayjnliqaexiioauy": {
        "name": "본회의부의안건",
        "name_en": "Plenary Session Agenda",
        "category": "bills",
        "mcp_tool": "get_plenary_agenda",
        "key_params": ["AGE", "SESS_NO"],
        "assembly_range": "22nd recommended",
        "notes": (
            "Bills placed on the plenary session agenda (upcoming floor votes). "
            "Distinct from pending bills (still in committee)."
        ),
        "verified": True,
    },

    # ================================================================
    # Members / 의원
    # ================================================================

    "ALLNAMEMBER": {
        "name": "역대 국회의원 정보",
        "name_en": "Historical National Assembly Member Information",
        "category": "members",
        "mcp_tool": "get_member_info",
        "key_params": ["NAAS_NM", "pIndex", "pSize"],
        "assembly_range": "16th-22nd",
        "notes": (
            "Preferred over nwvrqwxyaytdsfvhu. Returns correct per-assembly party, district, "
            "and committee data for multi-term members (slash-separated fields)."
        ),
        "verified": True,
    },

    "nwvrqwxyaytdsfvhu": {
        "name": "국회의원 정보 통합 API",
        "name_en": "National Assembly Member Information (Current Assembly Only)",
        "category": "members",
        "mcp_tool": None,
        "key_params": ["HG_NM", "POLY_NM", "ORIG_NM", "CMIT_NM"],
        "assembly_range": "Current assembly only",
        "notes": (
            "CAUTION: Ignores UNIT_CD — always returns current-assembly data regardless of "
            "the assembly requested. Use ALLNAMEMBER for historical or per-assembly queries."
        ),
        "verified": True,
    },

    # ================================================================
    # Votes / 표결
    # ================================================================

    "ncocpgfiaoituanbr": {
        "name": "의안별 표결현황",
        "name_en": "Plenary Vote Results by Bill (Aggregate Counts)",
        "category": "votes",
        "mcp_tool": "get_vote_results",
        "key_params": ["AGE", "BILL_NO", "BILL_NAME"],
        "assembly_range": "19th-22nd recommended",
        "notes": (
            "Aggregate yes/no/abstain counts per bill. The BILL_ID in results is needed "
            "to call nojepdqqaweusdfbi (get_member_votes) for per-member records."
        ),
        "verified": True,
    },

    "nojepdqqaweusdfbi": {
        "name": "국회의원 본회의 표결정보",
        "name_en": "Per-Member Plenary Vote Records",
        "category": "votes",
        "mcp_tool": "get_member_votes",
        "key_params": ["BILL_ID", "AGE", "HG_NM", "POLY_NM", "RESULT_VOTE_MOD"],
        "assembly_range": "18th-22nd recommended",
        "notes": (
            "One row per member per bill. Requires BILL_ID (PRC_...) + AGE. "
            "Default page_size=300 fetches all ~300 plenary members in one call. "
            "Filter by POLY_NM for party-discipline analysis."
        ),
        "verified": True,
    },

    # ================================================================
    # NARS / 국회입법조사처
    # ================================================================

    "naaborihbkorknasp": {
        "name": "국회입법조사처 보고서",
        "name_en": "NARS Research Reports (National Assembly Research Service)",
        "category": "nars",
        "mcp_tool": "search_nars_reports",
        "key_params": ["TITL_NM", "PUBLG_STRT_DT", "PUBLG_END_DT"],
        "assembly_range": "All (not assembly-specific)",
        "notes": (
            "입법조사처보고서, 이슈와논점, 외국법률동향과분석 등 NARS 발행 보고서 검색. "
            "Date params in YYYYMMDD format. Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,  # code confirmed, parameter names best-known
    },

    # ================================================================
    # Petitions / 청원
    # ================================================================

    "nvqbafvaajdiqhehi": {
        "name": "계류 청원",
        "name_en": "Pending Petitions",
        "category": "petitions",
        "mcp_tool": "search_petitions",
        "key_params": ["AGE", "PTTI_NM"],
        "assembly_range": "22nd recommended",
        "notes": (
            "청원 중 아직 심사 결과가 나오지 않은 계류 건. "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    "PTTRCP": {
        "name": "청원 접수 목록",
        "name_en": "Petition Receipt List",
        "category": "petitions",
        "mcp_tool": "search_petitions",
        "key_params": ["AGE", "PTTI_NM"],
        "assembly_range": "16th-22nd",
        "notes": (
            "전체 청원 접수 목록 (계류+종결 포함). "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    "PTTINFODETAIL": {
        "name": "청원 상세정보",
        "name_en": "Petition Detail",
        "category": "petitions",
        "mcp_tool": None,
        "key_params": ["PTTI_ID"],
        "assembly_range": "16th-22nd",
        "notes": "개별 청원 상세. Requires PTTI_ID. Use query_assembly.",
        "verified": False,
    },

    "PTTJUDGE": {
        "name": "청원 심사정보",
        "name_en": "Petition Review Information",
        "category": "petitions",
        "mcp_tool": None,
        "key_params": ["AGE", "PTTI_ID"],
        "assembly_range": "16th-22nd",
        "notes": "청원 심사 결과. Use query_assembly.",
        "verified": False,
    },

    "PTTCNTMAIN": {
        "name": "청원 통계",
        "name_en": "Petition Statistics (Aggregate)",
        "category": "petitions",
        "mcp_tool": None,
        "key_params": ["AGE"],
        "assembly_range": "All",
        "notes": "청원 집계 통계. Use query_assembly.",
        "verified": False,
    },

    # ================================================================
    # Schedule / 일정
    # ================================================================

    "ALLSCHEDULE": {
        "name": "국회 통합 일정",
        "name_en": "National Assembly Integrated Schedule",
        "category": "schedule",
        "mcp_tool": "get_schedule",
        "key_params": ["AGE", "UNIT_CD"],
        "assembly_range": "All",
        "notes": (
            "본회의·위원회·공청회 등 모든 일정 통합 조회 (90,201 records). "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    "nekcaiymatialqlxr": {
        "name": "본회의 일정",
        "name_en": "Plenary Session Schedule",
        "category": "schedule",
        "mcp_tool": "get_schedule",
        "key_params": ["AGE"],
        "assembly_range": "All",
        "notes": (
            "본회의 개최 일정만 필터링. "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    "nrsldhjpaemrmolla": {
        "name": "위원회 일정",
        "name_en": "Committee Schedule",
        "category": "schedule",
        "mcp_tool": "get_schedule",
        "key_params": ["AGE", "CMIT_NM"],
        "assembly_range": "All",
        "notes": (
            "위원회별 개최 일정. CMIT_NM으로 특정 위원회 필터 가능. "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    # ================================================================
    # Hearings / 청문회·공청회
    # ================================================================

    "VCONFCFRMCONFLIST": {
        "name": "인사청문회 목록",
        "name_en": "Personnel Confirmation Hearing List",
        "category": "hearings",
        "mcp_tool": "search_hearings",
        "key_params": ["AGE", "NAAS_NM"],
        "assembly_range": "16th-22nd",
        "notes": (
            "장관급 이상 인사청문회 목록. 후보자명 또는 위원회로 필터 가능. "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    "VCONFPHCONFLIST": {
        "name": "공청회 목록",
        "name_en": "Public Hearing List",
        "category": "hearings",
        "mcp_tool": "search_hearings",
        "key_params": ["AGE", "CMIT_NM"],
        "assembly_range": "16th-22nd",
        "notes": (
            "입법 공청회 목록 (51 records). 위원회별 필터 가능. "
            "Code sourced from hollobit/assembly-api-mcp."
        ),
        "verified": False,
    },

    # ================================================================
    # Meeting Records / 회의록
    # ================================================================

    "nzbyfwhwaoanttzje": {
        "name": "본회의 회의록",
        "name_en": "Plenary Session Minutes",
        "category": "meeting_records",
        "mcp_tool": None,
        "key_params": ["AGE", "CONF_DT"],
        "assembly_range": "All",
        "notes": (
            "본회의 회의 목록 (661 records). Full transcript text not available via API; "
            "this returns meeting metadata. Use query_assembly."
        ),
        "verified": False,
    },

    "ncwgseseafwbuheph": {
        "name": "위원회 회의록",
        "name_en": "Committee Session Minutes",
        "category": "meeting_records",
        "mcp_tool": None,
        "key_params": ["AGE", "CMIT_NM", "CONF_DT"],
        "assembly_range": "All",
        "notes": (
            "위원회 회의 목록 (12,822 records). Full transcript text not available via API; "
            "this returns meeting metadata. Use query_assembly."
        ),
        "verified": False,
    },

    # ================================================================
    # Committee Info / 위원회 정보 (additional)
    # ================================================================

    "nxrvzonlafugpqjuh": {
        "name": "위원회 정보",
        "name_en": "Committee Information",
        "category": "committees",
        "mcp_tool": None,
        "key_params": ["AGE", "CMIT_NM"],
        "assembly_range": "All",
        "notes": (
            "위원회 메타데이터: 이름, 종류, 소관. 356 records. Use query_assembly."
        ),
        "verified": False,
    },

    "nktulghcadyhmiqxi": {
        "name": "위원회 위원 명단",
        "name_en": "Committee Member Roster (Direct)",
        "category": "committees",
        "mcp_tool": None,
        "key_params": ["AGE", "CMIT_NM"],
        "assembly_range": "All",
        "notes": (
            "위원회별 위원 목록. 524 records. "
            "Use get_committee_members tool (ALLNAMEMBER-based) for better historical accuracy."
        ),
        "verified": False,
    },

    # ================================================================
    # Additional Bills (not yet covered by dedicated tools)
    # ================================================================

    "nzpltgfqabtcpsmai": {
        "name": "처리의안 목록",
        "name_en": "Processed Bills List",
        "category": "bills",
        "mcp_tool": None,
        "key_params": ["AGE", "BILL_NAME", "PROC_RESULT"],
        "assembly_range": "16th-22nd",
        "notes": (
            "처리 완료된 의안 목록 (가결, 부결, 폐기 등 포함). "
            "Use query_assembly. Complementary to search_bills."
        ),
        "verified": False,
    },

    "TVBPMBILL11": {
        "name": "의안 통합 검색",
        "name_en": "Integrated Bill Search",
        "category": "bills",
        "mcp_tool": None,
        "key_params": ["BILL_NAME", "AGE"],
        "assembly_range": "All",
        "notes": (
            "정부제출안 포함 전체 의안 통합 검색. "
            "Use query_assembly when government bills are needed."
        ),
        "verified": False,
    },
}


def search_registry(keyword: Optional[str] = None) -> dict[str, dict]:
    """Search the endpoint registry by keyword.

    Args:
        keyword: Case-insensitive substring to match against code, name,
                 name_en, category, mcp_tool, and notes. If None, returns
                 all entries.

    Returns:
        Filtered dict of {endpoint_code: metadata}.
    """
    if not keyword:
        return ENDPOINT_REGISTRY

    kw = keyword.lower()
    matches: dict[str, dict] = {}
    for code, info in ENDPOINT_REGISTRY.items():
        searchable = " ".join(filter(None, [
            code.lower(),
            info.get("name", "").lower(),
            info.get("name_en", "").lower(),
            info.get("category", "").lower(),
            info.get("mcp_tool") or "",
            info.get("notes", "").lower(),
            info.get("assembly_range", "").lower(),
        ]))
        if kw in searchable:
            matches[code] = info
    return matches


def group_by_category(endpoints: dict[str, dict]) -> dict[str, list[dict]]:
    """Group endpoint registry entries by category."""
    result: dict[str, list[dict]] = {}
    for code, info in endpoints.items():
        cat = info.get("category", "other")
        result.setdefault(cat, [])
        result[cat].append({"code": code, **info})
    return result
