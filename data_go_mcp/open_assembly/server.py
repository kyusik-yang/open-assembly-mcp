"""MCP server for Korean National Assembly Open API (open.assembly.go.kr)."""

import asyncio
import os
import sys
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .client import (
    AssemblyAPIClient,
    EP_NARS_REPORTS,
    EP_PETITION_PENDING,
    EP_PETITION_LIST,
    EP_SCHEDULE_ALL,
    EP_SCHEDULE_PLENARY,
    EP_SCHEDULE_COMMITTEE,
    EP_HEARING_CONFIRM,
    EP_HEARING_PUBLIC,
)

load_dotenv()

mcp = FastMCP("Korean National Assembly Open API")

UNIT_CD_MAP = {
    "22": "100022",
    "21": "100021",
    "20": "100020",
    "19": "100019",
    "18": "100018",
    "17": "100017",
    "16": "100016",
}


def _unit_cd(assembly: str) -> str:
    """Convert assembly string (e.g., '22') to UNIT_CD (e.g., '100022')."""
    return UNIT_CD_MAP.get(assembly, f"100{assembly.zfill(3)}")


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------


@mcp.tool()
async def search_bills(
    assembly: str,
    bill_name: Optional[str] = None,
    proposer: Optional[str] = None,
    proc_result: Optional[str] = None,
    committee: Optional[str] = None,
    propose_dt_from: Optional[str] = None,
    propose_dt_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    국회의원 발의법률안을 검색합니다 (의원발의안 전용; 정부제출안은 별도).

    Search for member-sponsored bills in the National Assembly.
    This is the PRIMARY entry point for most bill-related queries.

    IMPORTANT -- two bill identifiers are returned:
      - BILL_NO: 7-digit public number (e.g., "2216983") -- use with get_bill_detail, get_bill_review
      - BILL_ID: internal ID starting with "PRC_..." -- use with get_bill_proposers,
        get_member_votes, get_bill_committee_review

    Typical workflow:
      1. search_bills -> get list of bills with both BILL_NO and BILL_ID
      2. get_bill_proposers(bill_id=BILL_ID) -> co-sponsors
      3. get_member_votes(bill_id=BILL_ID, assembly=assembly) -> per-member vote records
      4. get_bill_review(assembly=assembly, bill_no=BILL_NO) -> committee/plenary timeline

    Note: covers member-initiated bills only. Does not include government-submitted bills.
    Date filtering (propose_dt_from/propose_dt_to) is applied client-side because the
    underlying API does not support it natively. When date filters are used with other
    filters (bill_name, committee, etc.), performance is good. Date-only queries on a
    full assembly may be slow (scans up to 2,000 results).

    For bill propose-reason texts (제안이유), use the korean-assembly-bills package
    (pip install korean-assembly-bills). 60,925 texts with 99.4% coverage (20th-22nd).

    Args:
        assembly: 대수 -- 필수 (예: "22" = 22대 국회, "16"-"22" 지원)
        bill_name: 법률안명 키워드 (선택, 예: "인공지능", "주거")
        proposer: 대표발의자명 (선택, 예: "홍길동")
        proc_result: 처리결과 필터 (선택) -- "원안가결" | "수정가결" | "부결" | "폐기"
        committee: 소관위원회명 (선택, 예: "법제사법위원회")
        propose_dt_from: 발의일 시작 (선택, 예: "2025-01-01") -- 클라이언트 사이드 필터링
        propose_dt_to: 발의일 종료 (선택, 예: "2025-12-31") -- 클라이언트 사이드 필터링
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10, 최대: 100)

    Returns:
        bills: 법률안 목록 -- 각 항목에 BILL_ID, BILL_NO, BILL_NAME, RST_PROPOSER,
               PROPOSE_DT, PROC_RESULT, COMMITTEE, DETAIL_LINK 포함
        count: 이번 페이지 반환 건수
        total_count: 검색 조건 전체 건수
        has_more: True이면 page+1로 재호출하여 추가 결과 조회 가능
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.search_bills(
                assembly=assembly,
                bill_name=bill_name,
                proposer=proposer,
                proc_result=proc_result,
                committee=committee,
                propose_dt_from=propose_dt_from,
                propose_dt_to=propose_dt_to,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}건 중 {len(rows)}건 반환 (페이지 {page})."
                if rows
                else "검색 결과가 없습니다."
            )
            return {
                "bills": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "bills": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_bill_detail(bill_no: str) -> dict[str, Any]:
    """
    의안 상세정보를 조회합니다 (의안정보 통합 API).

    Get comprehensive bill metadata: processing dates, committee referral, promulgation info,
    and a link to the official bill page.

    When to use:
      • After search_bills, to get the full metadata for a specific bill.
      • To get LINK_URL for the official bill text/rationale (not available via API).

    Not this tool:
      • For the committee/plenary processing TIMELINE → use get_bill_review
      • For CO-SPONSORS → use get_bill_proposers (requires BILL_ID, not BILL_NO)

    Bill full text / propose-reason (제안이유):
      The Open API does not return bill texts. Use the korean-assembly-bills package
      (pip install korean-assembly-bills) for 60,925 bill texts (20th-22nd Assembly).

    Args:
        bill_no: 의안번호 (예: "2217175") — 필수.
                 search_bills 또는 get_pending_bills 결과의 BILL_NO 필드 사용.
                 BILL_ID(PRC_...) 가 아닌 BILL_NO(숫자 7자리)를 사용해야 합니다.

    Returns:
        bill: 의안 상세정보 — BILL_NO, BILL_NM, BILL_KND, PPSR_NM, PPSL_DT,
              위원회 심사일정, 본회의 처리일정, 공포 정보, LINK_URL 등
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, _ = await client.get_bill_detail(bill_no=bill_no)
            if not rows:
                return {"bill": None, "message": f"의안번호 {bill_no}를 찾을 수 없습니다."}
            return {"bill": rows[0], "message": "조회 성공"}
        except Exception as e:
            return {"error": str(e), "bill": None}


@mcp.tool()
async def get_member_info(
    assembly: str = "22",
    name: Optional[str] = None,
    party: Optional[str] = None,
    district: Optional[str] = None,
    committee: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    국회의원 정보를 조회합니다.

    Query National Assembly member information: party, district, committee, contact, photo.
    Uses the ALLNAMEMBER endpoint to provide correct per-assembly data for all assemblies
    (16th-22nd). Party and district reflect each MP's actual affiliation during that assembly.

    When to use:
      - To look up a member's party, district, or committee affiliation.
      - To list all members of a party (use party filter, page through results).
      - To verify the exact name spelling before using as a filter in search_bills.

    For committee rosters specifically, get_committee_members is more direct.

    Args:
        assembly: 대수 (기본값: "22", "16"-"22" 지원)
        name: 의원 한글명 (선택, 예: "홍길동")
        party: 정당명 (선택, 예: "더불어민주당", "국민의힘")
        district: 선거구명 (선택, 예: "서울 강남갑", "비례대표")
        committee: 소속위원회명 (선택, 예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        members: 의원 목록 -- HG_NM(이름), POLY_NM(정당), ORIG_NM(선거구),
                 CMIT_NM(위원회), REELE_GBN_NM(선수), SEX_GBN_NM(성별),
                 E_MAIL, HOMEPAGE, NAAS_PIC(사진URL) 등
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_member_info(
                assembly=assembly,
                name=name,
                party=party,
                district=district,
                committee=committee,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}명 중 {len(rows)}명 반환 (페이지 {page})."
                if rows
                else "검색 결과가 없습니다."
            )
            return {
                "members": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "members": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_vote_results(
    assembly: str,
    bill_no: Optional[str] = None,
    bill_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    의안별 본회의 표결현황을 조회합니다 — 집계 결과(찬성/반대/기권 건수).

    Get plenary vote results by bill (aggregate yes/no/abstain counts).
    This is STEP 1 of the per-member vote analysis workflow.

    Typical vote analysis workflow:
      1. get_vote_results(assembly=assembly, bill_name=...) → find the bill, note its BILL_ID
      2. get_member_votes(bill_id=BILL_ID, assembly=assembly) → get per-member votes
      3. Filter votes by party, or compare party breakdowns

    NOT this tool:
      • For individual member votes → use get_member_votes (requires BILL_ID from this tool)

    Args:
        assembly: 대수 (예: "22") — 필수
        bill_no: 의안번호로 필터 (선택, 예: "2216983") — BILL_NO(숫자), BILL_ID 아님
        bill_name: 의안명 키워드로 필터 (선택, 예: "국민투표법")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        votes: 표결 목록 — BILL_ID(★ get_member_votes에 필요), BILL_NO, BILL_NAME,
               PROC_DT(표결일), MEMBER_TCNT(재석), VOTE_TCNT(투표),
               YES_TCNT(찬성), NO_TCNT(반대), BLANK_TCNT(기권),
               PROC_RESULT_CD(처리결과), LINK_URL
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_vote_results(
                assembly=assembly,
                bill_no=bill_no,
                bill_name=bill_name,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}건 중 {len(rows)}건 반환 (페이지 {page})."
                if rows
                else "검색 결과가 없습니다."
            )
            return {
                "votes": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "votes": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_bill_review(
    assembly: str,
    bill_no: Optional[str] = None,
    committee: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    의안 처리·심사정보를 조회합니다 — 위원회 및 본회의 처리 경로 요약.

    Get the high-level processing timeline for bills: committee referral date,
    committee decision, plenary vote date, and final outcome.

    NOT this tool:
      • For INDIVIDUAL COMMITTEE MEETING records (dates, agenda) → use get_bill_committee_review
      • For FULL BILL METADATA (proposer, LINK_URL, etc.) → use get_bill_detail
      • For PER-MEMBER VOTE records → use get_member_votes

    When to use:
      • To see the overall legislative timeline for one or more bills.
      • To filter bills by committee and see their processing status.

    Args:
        assembly: 대수 (예: "22") — 필수
        bill_no: 의안번호로 필터 (선택, 예: "2216983") — BILL_NO(숫자), BILL_ID 아님
        committee: 위원회명으로 필터 (선택, 예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        reviews: 심사정보 목록 — BILL_ID, BILL_NO, BILL_NM, COMMITTEE_NM,
                 위원회 상정일/의결일, 본회의 상정일/의결일, PROC_RESULT_CD(처리결과),
                 YES_TCNT, NO_TCNT, BLANK_TCNT, LAW_PROC_DT(공포일) 등
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_bill_review(
                assembly=assembly,
                bill_no=bill_no,
                committee=committee,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}건 중 {len(rows)}건 반환 (페이지 {page})."
                if rows
                else "검색 결과가 없습니다."
            )
            return {
                "reviews": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "reviews": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_bill_proposers(bill_id: str) -> dict[str, Any]:
    """
    의안 제안자(공동발의자) 정보를 조회합니다.

    Get the complete list of proposers (lead + all co-sponsors) for a bill.
    Returns name, party, and role for each proposer.

    When to use:
      • After search_bills, to find who co-sponsored a bill and from which parties.
      • For co-sponsorship network analysis across multiple bills.

    IMPORTANT — requires BILL_ID, not BILL_NO:
      • BILL_ID looks like "PRC_Y2Z6X0..." — get it from search_bills or get_pending_bills
      • BILL_NO is the 7-digit number (e.g., "2216983") — WRONG for this tool

    Args:
        bill_id: 의안ID — 필수 (예: "PRC_Y2Z6X0Y2W1X9V1W1D4E4D3B7B8Z1A1")
                 search_bills / get_pending_bills 결과의 BILL_ID 필드 사용.

    Returns:
        proposers: 제안자 목록 — PPSR_NM(이름), PPSR_POLY_NM(정당),
                   REP_DIV(대표/공동발의 구분), PPSR_ROLE(역할), PPSL_DT(발의일) 등
        count: 제안자 수
        total_count: 전체 제안자 수
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_bill_proposers(bill_id=bill_id)
            return {
                "proposers": rows,
                "count": len(rows),
                "total_count": total,
                "message": f"{len(rows)}명의 제안자 정보를 찾았습니다." if rows else "검색 결과가 없습니다.",
            }
        except Exception as e:
            return {"error": str(e), "proposers": [], "count": 0, "total_count": 0}


@mcp.tool()
async def get_member_votes(
    bill_id: str,
    assembly: str,
    member_name: Optional[str] = None,
    party: Optional[str] = None,
    vote_result: Optional[str] = None,
    page: int = 1,
    page_size: int = 300,
) -> dict[str, Any]:
    """
    특정 법안에 대한 국회의원 개인별 본회의 표결 기록을 조회합니다.

    Get individual member voting records for a specific bill (one row per member).
    This is STEP 2 of the per-member vote analysis workflow.

    Typical workflow:
      1. get_vote_results(assembly=assembly, bill_name=...) → find BILL_ID
      2. get_member_votes(bill_id=BILL_ID, assembly=assembly) → all ~300 member votes
      3. Filter by party="더불어민주당" etc. to analyze party discipline

    IMPORTANT — requires BILL_ID, not BILL_NO:
      • BILL_ID looks like "PRC_T2M6W0F2..." — get it from get_vote_results
      • BILL_NO is the 7-digit number — WRONG for this tool

    Note on default page_size=300:
      Intentionally large to fetch all ~300 plenary members in a single call.
      If the API returns fewer than 300 results but has_more=False, all votes are retrieved.

    Args:
        bill_id: 의안ID — 필수 (get_vote_results 결과의 BILL_ID 필드)
        assembly: 대수 — 필수 (예: "22")
        member_name: 의원명 필터 (선택, 예: "홍길동") — 특정 의원 표결만 조회할 때 사용
        party: 정당명 필터 (선택, 예: "더불어민주당") — 정당 기율 분석에 사용
        vote_result: 표결결과 필터 (선택) — "찬성" | "반대" | "기권"
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 300 — 본회의 전체 의원 한 번에 조회)

    Returns:
        votes: 의원별 표결 목록 — HG_NM(이름), POLY_NM(정당), ORIG_NM(선거구),
               RESULT_VOTE_MOD(표결결과: 찬성/반대/기권), VOTE_DATE, MONA_CD 등
        count: 이번 페이지 반환 건수
        total_count: 전체 표결 의원 수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_member_votes(
                bill_id=bill_id,
                assembly=assembly,
                member_name=member_name,
                party=party,
                vote_result=vote_result,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}명 중 {len(rows)}명 반환 (페이지 {page})."
                if rows
                else "표결 기록이 없습니다. BILL_ID(PRC_...)와 assembly(대수)를 확인하세요."
            )
            return {
                "votes": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "votes": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_committee_members(
    assembly: str = "22",
    committee: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    위원회 위원 명단을 조회합니다.

    Get the roster of a National Assembly committee, including party breakdown.

    When to use:
      • To list all members of a specific committee.
      • For party composition analysis of a committee.
      • More direct than get_member_info(committee=...) for committee rosters.

    Args:
        assembly: 대수 (기본값: "22", "16"–"22" 지원)
        committee: 위원회명 (선택, 예: "법제사법위원회", "과학기술정보방송통신위원회")
                   None이면 전체 의원 조회 (get_member_info와 동일)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 50 — 위원회 평균 규모)

    Returns:
        members: 위원 목록 — HG_NM(이름), POLY_NM(정당), ORIG_NM(선거구),
                 CMIT_NM(위원회), REELE_GBN_NM(선수), SEX_GBN_NM(성별) 등
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_committee_members(
                unit_cd=_unit_cd(assembly),
                committee=committee,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}명 중 {len(rows)}명 반환 (페이지 {page})."
                if rows
                else "검색 결과가 없습니다."
            )
            return {
                "members": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "members": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_pending_bills(
    assembly: str,
    bill_name: Optional[str] = None,
    committee: Optional[str] = None,
    proposer: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    현재 국회에 계류 중인 미처리 의안 목록을 조회합니다.

    Get bills currently pending (awaiting committee review or plenary vote).
    "Pending" excludes bills already passed, rejected, or withdrawn.

    When to use:
      • To see what legislation is currently active in a policy area.
      • To find unresolved bills on a topic.
      • Complements search_bills (which covers all outcomes including past bills).

    Args:
        assembly: 대수 (예: "22") — 필수
        bill_name: 법률안명 키워드로 필터 (선택)
        committee: 소관위원회명으로 필터 (선택, 예: "환경노동위원회")
        proposer: 대표발의자명으로 필터 (선택)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        bills: 계류의안 목록 — BILL_ID(★ get_bill_proposers 등에 필요),
               BILL_NO, BILL_NAME, PROPOSER, PROPOSE_DT, COMMITTEE 등
        count: 이번 페이지 반환 건수
        total_count: 전체 계류의안 수 (22대 기준 ~8,900건)
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_pending_bills(
                assembly=assembly,
                bill_name=bill_name,
                committee=committee,
                proposer=proposer,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}건의 계류의안 중 {len(rows)}건 반환 (페이지 {page})."
                if rows
                else "계류의안이 없습니다."
            )
            return {
                "bills": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "bills": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_plenary_agenda(
    assembly: str,
    session: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    본회의 부의안건 — 본회의에 상정된(또는 상정 예정인) 안건 목록을 조회합니다.

    Get bills placed on the plenary session agenda. Useful for tracking upcoming votes.

    When to use:
      • To see what bills are scheduled for the next plenary vote.
      • Complements get_pending_bills: pending bills are in committee;
        plenary agenda bills are ready for the floor vote.

    Args:
        assembly: 대수 (예: "22") — 필수
        session: 회기 번호로 필터 (선택, 예: "1" = 제1회기)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 20)

    Returns:
        agenda_items: 부의안건 목록 — BILL_ID, BILL_NO, BILL_NAME,
                      SESS_NO(회기), AGENDA_NO(안건번호), PROPOSE_DT, COMMITTEE 등
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_plenary_agenda(
                assembly=assembly,
                session=session,
                page=page,
                page_size=page_size,
            )
            has_more = total > page * page_size
            msg = (
                f"전체 {total}건의 본회의 부의안건 중 {len(rows)}건 반환 (페이지 {page})."
                if rows
                else "부의안건이 없습니다."
            )
            return {
                "agenda_items": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "message": msg,
            }
        except Exception as e:
            return {"error": str(e), "agenda_items": [], "count": 0, "total_count": 0, "has_more": False}


@mcp.tool()
async def get_bill_committee_review(bill_id: str) -> dict[str, Any]:
    """
    특정 의안의 위원회 심사 회의정보를 조회합니다.

    Get the individual committee meeting records at which a specific bill was reviewed.
    Returns one row per committee meeting, with date and result for each session.

    NOT this tool:
      • For the HIGH-LEVEL processing timeline (committee referral date, plenary vote date)
        → use get_bill_review (which takes BILL_NO, not BILL_ID)

    When to use:
      • To see exactly when and how many times a bill was discussed in committee.
      • Combined with get_bill_review for a complete legislative timeline.

    IMPORTANT — requires BILL_ID, not BILL_NO:
      • BILL_ID looks like "PRC_..." — get it from search_bills, get_pending_bills,
        get_vote_results, or get_bill_review
      • BILL_NO is the 7-digit public number — WRONG for this tool

    Args:
        bill_id: 의안ID — 필수 (예: "PRC_T2M6W0F2I1W2T1X7T4K2Q5A9J4P2M5")

    Returns:
        meetings: 위원회 심사 회의 목록 — BILL_ID, BILL_NM, CMIT_NM(위원회),
                  MTG_DT(회의일), SESS_NO(회기), PROC_RESULT(결과) 등
        count: 반환된 회의 수
        total_count: 전체 건수
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_bill_committee_review(bill_id=bill_id)
            return {
                "meetings": rows,
                "count": len(rows),
                "total_count": total,
                "message": (
                    f"{len(rows)}건의 위원회 심사 회의정보를 찾았습니다."
                    if rows
                    else "위원회 심사 회의정보가 없습니다. BILL_ID(PRC_...)를 확인하세요."
                ),
            }
        except Exception as e:
            return {"error": str(e), "meetings": [], "count": 0, "total_count": 0}


@mcp.tool()
async def get_bill_summary(assembly: str, bill_no: str) -> dict[str, Any]:
    """
    단일 의안의 핵심 정보를 한 번에 조회합니다 (편의 도구).

    One-shot summary of a single bill: metadata + processing timeline + co-sponsors +
    committee meeting history. Chains multiple API calls internally.

    When to use:
      • When you need a comprehensive view of ONE specific bill in a single call.
      • Instead of calling get_bill_detail + get_bill_review + get_bill_proposers separately.

    Note: This tool makes up to 3 parallel API calls. If any sub-call fails, that section
    will be missing from the result with an error note.

    Args:
        assembly: 대수 (예: "22") — 필수
        bill_no: 의안번호 (예: "2216983") — 필수.
                 search_bills / get_pending_bills 결과의 BILL_NO(숫자) 필드 사용.

    Returns:
        bill_no: 의안번호
        detail: get_bill_detail 결과 (BILL_NM, PPSR_NM, PPSL_DT, LINK_URL 등)
        review: get_bill_review 결과 (위원회/본회의 처리 타임라인, BILL_ID 포함)
        proposers: get_bill_proposers 결과 (공동발의자 목록)
        committee_meetings: get_bill_committee_review 결과 (위원회 심사 회의 목록)
        errors: 각 서브 호출의 에러 (정상이면 빈 dict)
    """
    async with AssemblyAPIClient() as client:
        errors: dict[str, str] = {}

        # Fetch detail and review in parallel
        detail_task = client.get_bill_detail(bill_no=bill_no)
        review_task = client.get_bill_review(assembly=assembly, bill_no=bill_no, page_size=1)
        detail_result, review_result = await asyncio.gather(
            detail_task, review_task, return_exceptions=True
        )

        detail_row = None
        if isinstance(detail_result, Exception):
            errors["detail"] = str(detail_result)
        elif detail_result[0]:
            detail_row = detail_result[0][0]

        review_row = None
        bill_id = None
        if isinstance(review_result, Exception):
            errors["review"] = str(review_result)
        elif review_result[0]:
            review_row = review_result[0][0]
            bill_id = review_row.get("BILL_ID") or review_row.get("BILL_NO")

        # Fetch proposers and committee meetings in parallel (need bill_id)
        proposers: list = []
        meetings: list = []
        if bill_id:
            prop_task = client.get_bill_proposers(bill_id=bill_id)
            mtg_task = client.get_bill_committee_review(bill_id=bill_id)
            prop_result, mtg_result = await asyncio.gather(
                prop_task, mtg_task, return_exceptions=True
            )
            if isinstance(prop_result, Exception):
                errors["proposers"] = str(prop_result)
            else:
                proposers = prop_result[0]
            if isinstance(mtg_result, Exception):
                errors["committee_meetings"] = str(mtg_result)
            else:
                meetings = mtg_result[0]
        else:
            errors["proposers"] = "BILL_ID not found — could not fetch co-sponsors"
            errors["committee_meetings"] = "BILL_ID not found — could not fetch committee meetings"

        return {
            "bill_no": bill_no,
            "detail": detail_row,
            "review": review_row,
            "proposers": proposers,
            "committee_meetings": meetings,
            "errors": errors,
            "message": (
                f"의안 {bill_no} 요약 조회 완료 "
                f"(공동발의자 {len(proposers)}명, 위원회 회의 {len(meetings)}건)."
                if not errors
                else f"의안 {bill_no} 일부 조회 실패: {list(errors.keys())}"
            ),
        }


@mcp.tool()
async def analyze_legislator(
    name: str,
    assembly: str = "22",
) -> dict[str, Any]:
    """
    국회의원 종합 프로필을 한 번에 조회합니다 (체인 도구).

    One-shot legislator profile: member info + all sponsored bills + career statistics.
    Internally chains get_member_info and search_bills.

    When to use:
      • When you need a complete picture of one legislator's activity in one call.
      • Instead of calling get_member_info + search_bills(proposer=name) separately.

    Note: Fetches up to 500 sponsored bills (5 pages of 100). For very prolific
    legislators total_count will be correct, but all[] may be truncated at 500.

    Args:
        name: 의원 한글명 — 필수 (예: "이준석", "홍길동")
               If multiple members share the name, the first result is used and
               all matches are listed in member_all_matches.
        assembly: 대수 (기본값: "22", "16"-"22" 지원)

    Returns:
        member: 의원 정보 dict (정당, 선거구, 위원회, 사진 등)
        member_all_matches: 동명이인이 있을 때 전체 목록
        bills:
          - total: 전체 발의 건수 (API 기준)
          - retrieved: 실제 가져온 건수 (최대 500)
          - by_result: 처리결과별 건수 {원안가결: N, 계류: N, ...}
          - by_committee: 소관위원회별 건수
          - by_year: 발의 연도별 건수
          - recent: 최근 발의 5건
          - all: 전체 발의 법안 목록 (최대 500건)
        errors: 서브 호출별 에러 (없으면 빈 dict)
        message: 요약 메시지
    """
    async with AssemblyAPIClient() as client:
        errors: dict[str, str] = {}

        # --- Step 1: member info + first bills page in parallel ---
        member_task = client.get_member_info(assembly=assembly, name=name, page_size=10)
        bills_task = client.search_bills(assembly=assembly, proposer=name, page=1, page_size=100)

        member_result, bills_result = await asyncio.gather(
            member_task, bills_task, return_exceptions=True
        )

        # Member info
        member: Optional[dict] = None
        member_all_matches: list[dict] = []
        if isinstance(member_result, Exception):
            errors["member"] = str(member_result)
        else:
            member_rows, member_total = member_result
            if not member_rows:
                errors["member"] = (
                    f"'{name}' 의원을 {assembly}대 국회에서 찾을 수 없습니다. "
                    "이름 철자나 대수를 확인하세요."
                )
            else:
                member = member_rows[0]
                member_all_matches = member_rows
                if member_total > 1:
                    errors["member_ambiguous"] = (
                        f"'{name}'이 {member_total}명 검색됨. "
                        f"첫 번째 결과 ({member.get('HG_NM')} / "
                        f"{member.get('POLY_NM')} / {member.get('ORIG_NM')})로 법안 조회."
                    )

        # Bills — first page
        all_bills: list[dict] = []
        bills_total = 0
        if isinstance(bills_result, Exception):
            errors["bills"] = str(bills_result)
        else:
            page_rows, bills_total = bills_result
            all_bills.extend(page_rows)

            # Sequential pagination for remaining pages (max 500 bills total)
            page = 2
            while len(all_bills) < bills_total and len(all_bills) < 500:
                try:
                    more_rows, _ = await client.search_bills(
                        assembly=assembly, proposer=name, page=page, page_size=100
                    )
                    if not more_rows:
                        break
                    all_bills.extend(more_rows)
                    page += 1
                except Exception as exc:
                    errors["bills_pagination"] = str(exc)
                    break

        # --- Step 2: compute statistics from retrieved bills ---
        by_result: dict[str, int] = {}
        by_committee: dict[str, int] = {}
        by_year: dict[str, int] = {}

        for bill in all_bills:
            # Processing result (None/empty = pending = 계류)
            result_key = bill.get("PROC_RESULT") or "계류"
            by_result[result_key] = by_result.get(result_key, 0) + 1

            # Committee
            cmit = bill.get("COMMITTEE") or "미배정"
            by_committee[cmit] = by_committee.get(cmit, 0) + 1

            # Year from PROPOSE_DT (handles "YYYYMMDD" and "YYYY-MM-DD")
            propose_dt = bill.get("PROPOSE_DT") or ""
            year = propose_dt[:4] if len(propose_dt) >= 4 and propose_dt[:4].isdigit() else "unknown"
            by_year[year] = by_year.get(year, 0) + 1

        # Sort by_year chronologically, by_result / by_committee by count descending
        by_result = dict(sorted(by_result.items(), key=lambda x: -x[1]))
        by_committee = dict(sorted(by_committee.items(), key=lambda x: -x[1]))
        by_year = dict(sorted(by_year.items()))

        # Most recent 5 bills
        recent = sorted(
            all_bills,
            key=lambda b: b.get("PROPOSE_DT") or "",
            reverse=True,
        )[:5]

        member_label = (
            f"{member.get('HG_NM')} ({member.get('POLY_NM')} | "
            f"{member.get('ORIG_NM')} | {assembly}대)"
            if member
            else name
        )

        return {
            "member": member,
            "member_all_matches": member_all_matches,
            "bills": {
                "total": bills_total,
                "retrieved": len(all_bills),
                "by_result": by_result,
                "by_committee": by_committee,
                "by_year": by_year,
                "recent": recent,
                "all": all_bills,
            },
            "errors": errors,
            "message": (
                f"{member_label}: 발의 법안 {bills_total}건 조회 완료."
                if not errors
                else f"{member_label}: 조회 완료 (일부 오류: {list(errors.keys())})."
            ),
        }


@mcp.tool()
async def get_party_cohesion(
    bill_id: str,
    assembly: str,
) -> dict[str, Any]:
    """
    특정 법안에 대한 정당별 표결 응집도를 분석합니다 (연구 전용 도구).

    Compute per-party voting cohesion for a bill:
      - yes/no/abstain counts per party
      - Rice index: |찬성 - 반대| / (찬성 + 반대) — 0 = perfect split, 1 = unanimous
      - dominant position per party (찬성 or 반대)
      - individual dissenters (voted against or abstained from party majority)

    Rice index excludes 기권 from the denominator (standard political science convention).
    기권 voters appear in dissenters["abstained"] when their party had a clear position.

    Typical workflow:
      1. get_vote_results(assembly=assembly, bill_name=...) → find BILL_ID
      2. get_party_cohesion(bill_id=BILL_ID, assembly=assembly) → cohesion analysis

    IMPORTANT — requires BILL_ID (PRC_...), not BILL_NO:
      • Get BILL_ID from get_vote_results, search_bills, or get_pending_bills.

    Args:
        bill_id: 의안ID — 필수 (PRC_... 형식, 예: "PRC_H2W6O0K2D1T1Y2B0...")
        assembly: 대수 — 필수 (예: "22")

    Returns:
        bill_id: 입력된 의안ID
        total_voted: 총 표결 의원 수 (찬성 + 반대 + 기권)
        overall: {"yes": N, "no": N, "abstain": N}
        by_party: 정당별 집계 (총 투표수 내림차순 정렬)
          Each party: {yes, no, abstain, total_voted, rice_index, dominant_position, unanimous}
        dissenters: 당론 이탈 의원 목록
          Each dissenter: {name, party, district, vote, party_dominant, type}
          type: "opposite" (당론 반대방향 투표) | "abstain" (당론 있는데 기권)
        errors: 에러 (없으면 빈 dict)
        message: 요약 메시지
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, _ = await client.get_member_votes(
                bill_id=bill_id,
                assembly=assembly,
                page_size=300,
            )
        except Exception as exc:
            return {
                "bill_id": bill_id,
                "error": str(exc),
                "total_voted": 0,
                "overall": {},
                "by_party": {},
                "dissenters": [],
                "errors": {"votes": str(exc)},
                "message": f"표결 기록 조회 실패: {exc}",
            }

        if not rows:
            return {
                "bill_id": bill_id,
                "total_voted": 0,
                "overall": {"yes": 0, "no": 0, "abstain": 0},
                "by_party": {},
                "dissenters": [],
                "errors": {},
                "message": (
                    "표결 기록이 없습니다. BILL_ID(PRC_...)와 assembly(대수)를 확인하세요. "
                    "get_vote_results에서 BILL_ID를 먼저 조회하세요."
                ),
            }

        # --- Aggregate votes by party ---
        # party_members: party -> list of {name, district, vote, mona_cd}
        party_members: dict[str, list[dict]] = {}
        for row in rows:
            party = row.get("POLY_NM") or "기타"
            vote = row.get("RESULT_VOTE_MOD") or ""
            party_members.setdefault(party, []).append({
                "name": row.get("HG_NM", ""),
                "district": row.get("ORIG_NM", ""),
                "vote": vote,
                "mona_cd": row.get("MONA_CD", ""),
            })

        # --- Compute cohesion stats per party ---
        by_party: dict[str, dict] = {}
        for party, members in party_members.items():
            yes = sum(1 for m in members if m["vote"] == "찬성")
            no = sum(1 for m in members if m["vote"] == "반대")
            abstain = sum(1 for m in members if m["vote"] not in ("찬성", "반대"))
            total = yes + no + abstain

            decisive = yes + no  # 기권 제외 (Rice index 분모)
            if decisive > 0:
                rice_index = round(abs(yes - no) / decisive, 4)
                dominant_position: Optional[str] = "찬성" if yes >= no else "반대"
            else:
                rice_index = None  # 전원 기권 — 지배적 포지션 없음
                dominant_position = None

            unanimous = decisive > 0 and (yes == 0 or no == 0)

            by_party[party] = {
                "yes": yes,
                "no": no,
                "abstain": abstain,
                "total_voted": total,
                "rice_index": rice_index,
                "dominant_position": dominant_position,
                "unanimous": unanimous,
            }

        # --- Identify dissenters ---
        dissenters: list[dict] = []
        for party, members in party_members.items():
            dominant = by_party[party]["dominant_position"]
            if dominant is None:
                continue  # 지배적 포지션이 없으면 이탈자 없음
            for m in members:
                vote = m["vote"]
                is_opposite = (
                    (dominant == "찬성" and vote == "반대")
                    or (dominant == "반대" and vote == "찬성")
                )
                is_abstain = vote not in ("찬성", "반대")
                if is_opposite or is_abstain:
                    dissenters.append({
                        "name": m["name"],
                        "party": party,
                        "district": m["district"],
                        "vote": vote,
                        "party_dominant": dominant,
                        "type": "opposite" if is_opposite else "abstain",
                    })

        # --- Totals and sorting ---
        overall_yes = sum(d["yes"] for d in by_party.values())
        overall_no = sum(d["no"] for d in by_party.values())
        overall_abstain = sum(d["abstain"] for d in by_party.values())
        total_voted = overall_yes + overall_no + overall_abstain

        by_party = dict(sorted(by_party.items(), key=lambda x: -x[1]["total_voted"]))
        dissenters.sort(key=lambda x: (x["party"], x["name"]))

        return {
            "bill_id": bill_id,
            "total_voted": total_voted,
            "overall": {"yes": overall_yes, "no": overall_no, "abstain": overall_abstain},
            "by_party": by_party,
            "dissenters": dissenters,
            "errors": {},
            "message": (
                f"총 {total_voted}명 표결 — 찬성 {overall_yes} / 반대 {overall_no} / 기권 {overall_abstain}. "
                f"{len(by_party)}개 정당, 당론 이탈 {len(dissenters)}명."
            ),
        }


@mcp.tool()
async def search_nars_reports(
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    국회입법조사처(NARS) 보고서를 검색합니다.

    Search publications from the National Assembly Research Service (NARS / 국회입법조사처):
    research reports (입법조사처보고서), issue briefs (이슈와논점), foreign law trends
    (외국법률동향과분석), and regular reports (정기보고서).

    NARS reports provide authoritative background on policy issues — useful for
    understanding the legislative context around any bill or policy domain.

    Note: This tool uses endpoint naaborihbkorknasp. Parameter names are based on
    the open.assembly.go.kr API pattern and hollobit/assembly-api-mcp source review.
    If the keyword filter does not work as expected, try query_assembly with
    discover_apis(keyword="NARS") to inspect the raw response schema.

    Args:
        keyword: 보고서 제목 키워드 (선택, 예: "인공지능", "복지", "조세")
        date_from: 발행일 시작 (선택, YYYYMMDD 형식, 예: "20240101")
        date_to: 발행일 종료 (선택, YYYYMMDD 형식, 예: "20241231")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10, 최대: 100)

    Returns:
        reports: 보고서 목록 — 각 항목에 제목, 발행일, 저자, 보고서 유형 등 포함
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
        raw_response: 비표준 응답 형식일 때 전체 JSON
    """
    params: dict[str, Any] = {"pIndex": page, "pSize": page_size}
    if keyword:
        params["TITL_NM"] = keyword
    if date_from:
        params["PUBLG_STRT_DT"] = date_from
    if date_to:
        params["PUBLG_END_DT"] = date_to

    async with AssemblyAPIClient() as client:
        try:
            rows, total, raw = await client.query_endpoint(EP_NARS_REPORTS, params)

            if raw is not None:
                return {
                    "reports": [],
                    "count": 0,
                    "total_count": 0,
                    "has_more": False,
                    "raw_response": raw,
                    "message": (
                        "비표준 응답 형식. raw_response에서 직접 확인하세요. "
                        "파라미터명이 다를 수 있습니다 — query_assembly로 직접 호출해보세요."
                    ),
                }

            has_more = total > page * page_size
            return {
                "reports": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "raw_response": None,
                "message": (
                    f"전체 {total}건 중 {len(rows)}건 반환 (페이지 {page})."
                    if rows
                    else "검색 결과가 없습니다."
                ),
            }
        except Exception as e:
            return {
                "error": str(e),
                "reports": [],
                "count": 0,
                "total_count": 0,
                "has_more": False,
                "raw_response": None,
            }


@mcp.tool()
async def search_petitions(
    assembly: str,
    keyword: Optional[str] = None,
    include_closed: bool = False,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    국회 청원 목록을 조회합니다.

    Query petition records from the National Assembly: pending petitions (계류 청원)
    or all petitions including closed ones (접수 목록).

    Petitions (청원) are formal citizen requests submitted through National Assembly members.
    This tool returns petition metadata — title, proposer, assembly, committee, status.

    Note: Full petition text is not available through the Open API. This tool returns
    petition records/status, not the content of individual petitions. For research on
    citizen engagement and petition outcomes, the status and committee routing data
    returned here is typically sufficient.

    Parameter names are based on the API pattern and hollobit/assembly-api-mcp source.
    If keyword filtering does not return expected results, use query_assembly directly:
      discover_apis(keyword="청원") → query_assembly(endpoint_code="PTTRCP", params={...})

    Args:
        assembly: 대수 — 필수 (예: "22")
        keyword: 청원 제목 키워드 (선택, 예: "교육", "환경")
        include_closed: True이면 처리 완료 청원까지 포함 (PTTRCP 엔드포인트 사용).
                        False이면 계류 중인 청원만 반환 (기본값, nvqbafvaajdiqhehi 사용).
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        petitions: 청원 목록
        endpoint_used: 실제 호출된 엔드포인트 코드
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
        raw_response: 비표준 응답 형식일 때 전체 JSON
    """
    endpoint = EP_PETITION_LIST if include_closed else EP_PETITION_PENDING
    params: dict[str, Any] = {"AGE": assembly, "pIndex": page, "pSize": page_size}
    if keyword:
        params["PTTI_NM"] = keyword

    async with AssemblyAPIClient() as client:
        try:
            rows, total, raw = await client.query_endpoint(endpoint, params)

            if raw is not None:
                return {
                    "petitions": [],
                    "endpoint_used": endpoint,
                    "count": 0,
                    "total_count": 0,
                    "has_more": False,
                    "raw_response": raw,
                    "message": (
                        f"{endpoint}: 비표준 응답 형식. raw_response에서 직접 확인하세요."
                    ),
                }

            has_more = total > page * page_size
            scope = "계류 청원" if not include_closed else "전체 청원 접수"
            return {
                "petitions": rows,
                "endpoint_used": endpoint,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "raw_response": None,
                "message": (
                    f"{assembly}대 {scope}: 전체 {total}건 중 {len(rows)}건 반환."
                    if rows
                    else f"{assembly}대 {scope}: 결과가 없습니다."
                ),
            }
        except Exception as e:
            return {
                "error": str(e),
                "petitions": [],
                "endpoint_used": endpoint,
                "count": 0,
                "total_count": 0,
                "has_more": False,
                "raw_response": None,
            }


@mcp.tool()
async def get_schedule(
    assembly: str,
    schedule_type: str = "all",
    committee: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    국회 일정을 조회합니다 (본회의·위원회·공청회 등).

    Query the National Assembly schedule: plenary sessions, committee meetings,
    public hearings, and other proceedings.

    Schedule type determines which endpoint is used:
      - "all"       → ALLSCHEDULE (모든 종류 통합, 가장 포괄적)
      - "plenary"   → nekcaiymatialqlxr (본회의만)
      - "committee" → nrsldhjpaemrmolla (위원회만, committee 필터 사용 가능)

    Note: Parameter names are based on the API pattern. If date filtering or
    committee filtering does not work as expected, use query_assembly directly.

    Args:
        assembly: 대수 — 필수 (예: "22")
        schedule_type: 일정 종류 — "all" (기본값) | "plenary" | "committee"
        committee: 위원회명 필터 (선택, schedule_type="committee"일 때만 적용,
                   예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 20)

    Returns:
        schedule_items: 일정 목록
        endpoint_used: 실제 호출된 엔드포인트 코드
        schedule_type: 요청한 일정 종류
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
        raw_response: 비표준 응답 형식일 때 전체 JSON
    """
    schedule_type = schedule_type.lower()
    if schedule_type == "plenary":
        endpoint = EP_SCHEDULE_PLENARY
    elif schedule_type == "committee":
        endpoint = EP_SCHEDULE_COMMITTEE
    else:
        endpoint = EP_SCHEDULE_ALL
        schedule_type = "all"

    params: dict[str, Any] = {"AGE": assembly, "pIndex": page, "pSize": page_size}
    if committee and schedule_type == "committee":
        params["CMIT_NM"] = committee

    async with AssemblyAPIClient() as client:
        try:
            rows, total, raw = await client.query_endpoint(endpoint, params)

            if raw is not None:
                return {
                    "schedule_items": [],
                    "endpoint_used": endpoint,
                    "schedule_type": schedule_type,
                    "count": 0,
                    "total_count": 0,
                    "has_more": False,
                    "raw_response": raw,
                    "message": (
                        f"{endpoint}: 비표준 응답 형식. raw_response에서 직접 확인하세요."
                    ),
                }

            has_more = total > page * page_size
            type_label = {"all": "통합", "plenary": "본회의", "committee": "위원회"}.get(
                schedule_type, schedule_type
            )
            return {
                "schedule_items": rows,
                "endpoint_used": endpoint,
                "schedule_type": schedule_type,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "raw_response": None,
                "message": (
                    f"{assembly}대 {type_label} 일정: 전체 {total}건 중 {len(rows)}건 반환."
                    if rows
                    else f"{assembly}대 {type_label} 일정: 결과가 없습니다."
                ),
            }
        except Exception as e:
            return {
                "error": str(e),
                "schedule_items": [],
                "endpoint_used": endpoint,
                "schedule_type": schedule_type,
                "count": 0,
                "total_count": 0,
                "has_more": False,
                "raw_response": None,
            }


@mcp.tool()
async def search_hearings(
    assembly: str,
    hearing_type: str = "confirmation",
    nominee_name: Optional[str] = None,
    committee: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    국회 인사청문회 및 공청회 목록을 조회합니다.

    Query National Assembly confirmation hearings (인사청문회) or public hearings (공청회).

    Hearing types:
      - "confirmation": 인사청문회 — personnel confirmation hearings for cabinet nominees,
        agency heads, and other senior appointees. Use nominee_name to filter by candidate.
      - "public": 공청회 — legislative public hearings for citizen input on bills.
        Use committee to filter by committee.

    Research use case: For analysis of confirmation hearings and political appointments,
    combine with the kr-hearings-data package (9.9M speeches, 7.9M dyads) which
    provides full transcript-level data. This tool returns hearing metadata only.

    Note: Parameter names are based on the API pattern and hollobit/assembly-api-mcp
    source review. If nominee_name filtering does not work, use query_assembly directly.

    Args:
        assembly: 대수 — 필수 (예: "22")
        hearing_type: 청문회 유형 — "confirmation" 인사청문회 (기본값) | "public" 공청회
        nominee_name: 후보자 이름 필터 (선택, hearing_type="confirmation"일 때 사용,
                      예: "홍길동")
        committee: 위원회명 필터 (선택, 예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        hearings: 청문회 목록 — 청문회 날짜, 대상자/의안, 위원회 등
        endpoint_used: 실제 호출된 엔드포인트 코드
        hearing_type: 요청한 청문회 유형
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
        raw_response: 비표준 응답 형식일 때 전체 JSON
    """
    hearing_type = hearing_type.lower()
    endpoint = EP_HEARING_CONFIRM if hearing_type == "confirmation" else EP_HEARING_PUBLIC

    params: dict[str, Any] = {"AGE": assembly, "pIndex": page, "pSize": page_size}
    if nominee_name:
        params["NAAS_NM"] = nominee_name
    if committee:
        params["CMIT_NM"] = committee

    async with AssemblyAPIClient() as client:
        try:
            rows, total, raw = await client.query_endpoint(endpoint, params)

            if raw is not None:
                return {
                    "hearings": [],
                    "endpoint_used": endpoint,
                    "hearing_type": hearing_type,
                    "count": 0,
                    "total_count": 0,
                    "has_more": False,
                    "raw_response": raw,
                    "message": (
                        f"{endpoint}: 비표준 응답 형식. raw_response에서 직접 확인하세요."
                    ),
                }

            has_more = total > page * page_size
            type_label = "인사청문회" if hearing_type == "confirmation" else "공청회"
            return {
                "hearings": rows,
                "endpoint_used": endpoint,
                "hearing_type": hearing_type,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "raw_response": None,
                "message": (
                    f"{assembly}대 {type_label}: 전체 {total}건 중 {len(rows)}건 반환."
                    if rows
                    else f"{assembly}대 {type_label}: 결과가 없습니다."
                ),
            }
        except Exception as e:
            return {
                "error": str(e),
                "hearings": [],
                "endpoint_used": endpoint,
                "hearing_type": hearing_type,
                "count": 0,
                "total_count": 0,
                "has_more": False,
                "raw_response": None,
            }


@mcp.tool()
async def discover_apis(keyword: Optional[str] = None) -> dict[str, Any]:
    """
    열린국회정보 Open API 엔드포인트를 검색합니다.

    Search the registry of verified Korean National Assembly API endpoints.
    Use this to find the endpoint code you need before calling query_assembly.

    Typical workflow:
      1. discover_apis(keyword="청원") → find petition endpoint codes
      2. query_assembly(endpoint_code="<code>", params={"AGE": "22"}) → call it

    When to use:
      • To explore what API endpoints are available beyond the 12 dedicated tools.
      • To find the endpoint code for a specific data type (schedule, petitions, etc.).
      • Without a keyword to see all verified endpoints organized by category.

    Note: This registry covers the verified subset of the 276+ endpoints available at
    open.assembly.go.kr. If your endpoint is not here, visit the API portal directly:
    https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do

    Args:
        keyword: 검색어 (선택, 예: "청원", "일정", "petition", "vote").
                 Matches against Korean name, English name, category, tool name, and notes.
                 If omitted, returns all verified endpoints grouped by category.

    Returns:
        endpoints: List of matching endpoints with code, names, key_params, and notes
        by_category: Same endpoints grouped by category (bills, members, votes, ...)
        count: Number of matching endpoints
        note: Link to the full API catalog
    """
    from .registry import search_registry, group_by_category

    matches = search_registry(keyword)
    by_category = group_by_category(matches)

    endpoint_list = [{"code": code, **info} for code, info in matches.items()]

    return {
        "endpoints": endpoint_list,
        "by_category": by_category,
        "count": len(matches),
        "message": (
            f"'{keyword}' 검색 결과: {len(matches)}개 엔드포인트"
            if keyword and matches
            else f"'{keyword}'에 해당하는 엔드포인트가 없습니다. 키워드를 바꿔 다시 시도하거나 query_assembly에서 직접 코드를 입력하세요."
            if keyword
            else f"전체 {len(matches)}개 검증된 엔드포인트 (열린국회 276+ 중 직접 테스트 완료)"
        ),
        "note": (
            "전체 API 카탈로그 (276+): "
            "https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do"
        ),
    }


@mcp.tool()
async def query_assembly(
    endpoint_code: str,
    params: Optional[dict] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """
    열린국회정보 Open API의 임의 엔드포인트를 직접 호출합니다 (범용 fallback).

    Universal fallback tool — call any open.assembly.go.kr API endpoint directly.
    Use when no dedicated MCP tool exists for the data you need.

    Typical workflow:
      1. discover_apis(keyword="청원") → find the right endpoint code
      2. query_assembly(endpoint_code="<code>", params={"AGE": "22"}) → call it

    Authentication (ASSEMBLY_API_KEY) is handled automatically — do NOT pass KEY in params.

    Common parameters across most endpoints:
      - AGE: assembly number (e.g., "22" for 22nd Assembly)
      - pIndex / pSize: pagination — handled via page / page_size args here

    Args:
        endpoint_code: API 엔드포인트 코드 (예: "nzmimeepazxkubdpn").
                       discover_apis()로 코드를 먼저 확인하거나,
                       https://open.assembly.go.kr에서 직접 조회.
        params: 추가 API 파라미터 (선택, 예: {"AGE": "22", "BILL_NAME": "인공지능"}).
                KEY, Type, pIndex, pSize는 자동 처리되므로 포함 불필요.
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10, 최대: 100)

    Returns:
        endpoint: 호출된 엔드포인트 코드
        rows: 결과 행 목록 (표준 응답 형식일 때)
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출 가능
        raw_response: 비표준 응답 형식일 때 전체 JSON (rows 대신 이걸 확인)
    """
    merged_params: dict[str, Any] = {"pIndex": page, "pSize": page_size}
    if params:
        merged_params.update(params)

    async with AssemblyAPIClient() as client:
        try:
            rows, total, raw = await client.query_endpoint(endpoint_code, merged_params)

            if raw is not None:
                # Non-standard response format
                return {
                    "endpoint": endpoint_code,
                    "rows": [],
                    "count": 0,
                    "total_count": 0,
                    "has_more": False,
                    "raw_response": raw,
                    "message": (
                        f"{endpoint_code}: 비표준 응답 형식. raw_response에서 직접 확인하세요. "
                        "discover_apis()로 이 엔드포인트에 대한 전용 도구가 있는지 확인해보세요."
                    ),
                }

            has_more = total > page * page_size
            return {
                "endpoint": endpoint_code,
                "rows": rows,
                "count": len(rows),
                "total_count": total,
                "has_more": has_more,
                "raw_response": None,
                "message": (
                    f"{endpoint_code}: {len(rows)}/{total}건 반환 (페이지 {page})."
                    if rows
                    else f"{endpoint_code}: 결과가 없습니다. 파라미터를 확인하세요."
                ),
            }
        except Exception as e:
            return {
                "endpoint": endpoint_code,
                "error": str(e),
                "rows": [],
                "count": 0,
                "total_count": 0,
                "has_more": False,
                "raw_response": None,
            }


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def main() -> None:
    if "--setup" in sys.argv:
        from .setup_cli import run_setup
        run_setup()
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    api_key = os.getenv("ASSEMBLY_API_KEY")
    if not api_key:
        logging.error("ASSEMBLY_API_KEY environment variable is not set.")
        logging.error("Run 'uvx open-assembly-mcp --setup' for interactive setup.")
        logging.error("Or sign up at https://open.assembly.go.kr to get your API key.")
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
