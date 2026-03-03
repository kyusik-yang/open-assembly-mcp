"""MCP server for Korean National Assembly Open API (open.assembly.go.kr)."""

import asyncio
import os
import sys
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .client import AssemblyAPIClient

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


def _unit_cd(age: str) -> str:
    """Convert assembly age string (e.g., '22') to UNIT_CD (e.g., '100022')."""
    return UNIT_CD_MAP.get(age, f"100{age.zfill(3)}")


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------


@mcp.tool()
async def search_bills(
    age: str,
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

    IMPORTANT — two bill identifiers are returned:
      • BILL_NO: 7-digit public number (e.g., "2216983") — use with get_bill_detail, get_bill_review
      • BILL_ID: internal ID starting with "PRC_..." — use with get_bill_proposers,
        get_member_votes, get_bill_committee_review

    Typical workflow:
      1. search_bills → get list of bills with both BILL_NO and BILL_ID
      2. get_bill_proposers(bill_id=BILL_ID) → co-sponsors
      3. get_member_votes(bill_id=BILL_ID, age=age) → per-member vote records
      4. get_bill_review(age=age, bill_no=BILL_NO) → committee/plenary timeline

    Note: covers member-initiated bills only. Does not include government-submitted bills.

    Args:
        age: 대수 — 필수 (예: "22" = 22대 국회, "16"–"22" 지원)
        bill_name: 법률안명 키워드 (선택, 예: "인공지능", "주거")
        proposer: 대표발의자명 (선택, 예: "홍길동")
        proc_result: 처리결과 필터 (선택) — "원안가결" | "수정가결" | "부결" | "폐기"
        committee: 소관위원회명 (선택, 예: "법제사법위원회")
        propose_dt_from: 발의일 시작 (선택, YYYYMMDD 형식, 예: "20240101")
        propose_dt_to: 발의일 종료 (선택, YYYYMMDD 형식, 예: "20241231")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10, 최대: 100)

    Returns:
        bills: 법률안 목록 — 각 항목에 BILL_ID, BILL_NO, BILL_NAME, RST_PROPOSER,
               PROPOSE_DT, PROC_RESULT, COMMITTEE, DETAIL_LINK 포함
        count: 이번 페이지 반환 건수
        total_count: 검색 조건 전체 건수
        has_more: True이면 page+1로 재호출하여 추가 결과 조회 가능
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.search_bills(
                age=age,
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
    age: str = "22",
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

    When to use:
      • To look up a member's party, district, or committee affiliation.
      • To list all members of a party (use party filter, page through results).
      • To verify the exact name spelling before using as a filter in search_bills.

    For committee rosters specifically, get_committee_members is more direct.

    Args:
        age: 대수 (기본값: "22", "16"–"22" 지원)
        name: 의원 한글명 (선택, 예: "홍길동") — 정확한 이름이어야 합니다
        party: 정당명 (선택, 예: "더불어민주당", "국민의힘")
        district: 선거구명 (선택, 예: "서울 강남갑", "비례대표")
        committee: 소속위원회명 (선택, 예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        members: 의원 목록 — HG_NM(이름), POLY_NM(정당), ORIG_NM(선거구),
                 CMIT_NM(위원회), REELE_GBN_NM(선수), SEX_GBN_NM(성별),
                 TEL_NO, E_MAIL, HOMEPAGE, NAAS_PIC(사진URL) 등
        count: 이번 페이지 반환 건수
        total_count: 전체 건수
        has_more: True이면 page+1로 재호출
    """
    async with AssemblyAPIClient() as client:
        try:
            rows, total = await client.get_member_info(
                unit_cd=_unit_cd(age),
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
    age: str,
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
      1. get_vote_results(age=age, bill_name=...) → find the bill, note its BILL_ID
      2. get_member_votes(bill_id=BILL_ID, age=age) → get per-member votes
      3. Filter votes by party, or compare party breakdowns

    NOT this tool:
      • For individual member votes → use get_member_votes (requires BILL_ID from this tool)

    Args:
        age: 대수 (예: "22") — 필수
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
                age=age,
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
    age: str,
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
        age: 대수 (예: "22") — 필수
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
                age=age,
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
    age: str,
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
      1. get_vote_results(age=age, bill_name=...) → find BILL_ID
      2. get_member_votes(bill_id=BILL_ID, age=age) → all ~300 member votes
      3. Filter by party="더불어민주당" etc. to analyze party discipline

    IMPORTANT — requires BILL_ID, not BILL_NO:
      • BILL_ID looks like "PRC_T2M6W0F2..." — get it from get_vote_results
      • BILL_NO is the 7-digit number — WRONG for this tool

    Note on default page_size=300:
      Intentionally large to fetch all ~300 plenary members in a single call.
      If the API returns fewer than 300 results but has_more=False, all votes are retrieved.

    Args:
        bill_id: 의안ID — 필수 (get_vote_results 결과의 BILL_ID 필드)
        age: 대수 — 필수 (예: "22")
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
                age=age,
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
                else "표결 기록이 없습니다. BILL_ID(PRC_...)와 AGE를 확인하세요."
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
    age: str = "22",
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
        age: 대수 (기본값: "22", "16"–"22" 지원)
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
                unit_cd=_unit_cd(age),
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
    age: str,
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
        age: 대수 (예: "22") — 필수
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
                age=age,
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
    age: str,
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
        age: 대수 (예: "22") — 필수
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
                age=age,
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
async def get_bill_summary(age: str, bill_no: str) -> dict[str, Any]:
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
        age: 대수 (예: "22") — 필수
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
        review_task = client.get_bill_review(age=age, bill_no=bill_no, page_size=1)
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
