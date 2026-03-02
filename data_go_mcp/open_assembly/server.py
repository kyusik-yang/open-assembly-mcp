"""MCP server for Korean National Assembly Open API (open.assembly.go.kr)."""

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
    """대수 문자열을 UNIT_CD로 변환."""
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
    Note: covers member-initiated bills only, not government-submitted bills.

    Args:
        age: 대수 (예: "22" = 22대 국회, "16"~"22" 지원) — 필수
        bill_name: 법률안명 키워드 (선택)
        proposer: 대표발의자명 (선택)
        proc_result: 처리결과 필터 — "원안가결" | "수정가결" | "부결" | "폐기" (선택)
        committee: 소관위원회명 (선택)
        propose_dt_from: 발의일 시작 (선택, YYYYMMDD 형식)
        propose_dt_to: 발의일 종료 (선택, YYYYMMDD 형식)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10, 최대: 100)

    Returns:
        bills: 법률안 목록 (BILL_ID, BILL_NO, BILL_NAME, RST_PROPOSER, PUBL_PROPOSER,
               PROPOSE_DT, PROC_RESULT, COMMITTEE, DETAIL_LINK 등)
        count: 반환된 건수
        total_count: 검색 조건에 해당하는 전체 건수
        has_more: 다음 페이지 존재 여부
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

    Get comprehensive bill information including processing history.
    For bill text and rationale, follow the LINK_URL field in the result.

    Args:
        bill_no: 의안번호 (예: "2217175") — 필수. search_bills 결과의 BILL_NO 사용.

    Returns:
        bill: 의안 상세정보 (BILL_NO, BILL_NM, BILL_KND, PPSR_NM, PPSL_DT,
              위원회 심사일정, 본회의 처리일정, 공포 정보, LINK_URL 등)
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

    Query National Assembly member information.

    Args:
        age: 대수 (예: "22" = 22대, "16"~"22" 지원) (기본값: "22")
        name: 의원 한글명 (선택, 예: "홍길동")
        party: 정당명 (선택, 예: "더불어민주당", "국민의힘")
        district: 선거구명 (선택, 예: "서울 강남갑", "비례대표")
        committee: 소속위원회명 (선택, 예: "법제사법위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        members: 의원 목록 (HG_NM, POLY_NM, ORIG_NM, CMIT_NM, REELE_GBN_NM,
                 SEX_GBN_NM, TEL_NO, E_MAIL, HOMEPAGE, MONA_CD, ASSEM_ADDR 등)
        count: 반환된 건수
        total_count: 전체 건수
        has_more: 다음 페이지 존재 여부
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
    의안별 본회의 표결현황을 조회합니다 (집계: 찬성/반대/기권 건수).

    Get plenary vote results by bill (aggregate counts: yes/no/abstain).
    For individual member voting records, the Open API does not provide a per-member endpoint.

    Args:
        age: 대수 (예: "22") — 필수
        bill_no: 의안번호로 필터 (선택)
        bill_name: 의안명 키워드로 필터 (선택)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        votes: 표결 목록 (BILL_NO, BILL_NAME, PROC_DT, MEMBER_TCNT,
               VOTE_TCNT, YES_TCNT, NO_TCNT, BLANK_TCNT, PROC_RESULT_CD, LINK_URL 등)
        count: 반환된 건수
        total_count: 전체 건수
        has_more: 다음 페이지 존재 여부
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
    의안 처리·심사정보를 조회합니다 (위원회 및 본회의 처리 경로).

    Get bill review and processing information (committee + plenary timeline).

    Args:
        age: 대수 (예: "22") — 필수
        bill_no: 의안번호 (선택)
        committee: 위원회명으로 필터 (선택)
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 10)

    Returns:
        reviews: 심사정보 목록 (BILL_NO, BILL_NM, COMMITTEE_NM, PROC_RESULT_CD,
                 위원회 및 본회의 처리 일정, 표결 결과 등)
        count: 반환된 건수
        total_count: 전체 건수
        has_more: 다음 페이지 존재 여부
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

    Get the list of all proposers (lead and co-sponsors) for a bill.

    Args:
        bill_id: 의안ID (search_bills 결과의 BILL_ID, 예: "PRC_Y2Z6X0...") — 필수
                 BILL_NO(숫자)가 아닌 BILL_ID(PRC_...)를 사용해야 합니다.

    Returns:
        proposers: 제안자 목록 (PPSR_NM, PPSR_POLY_NM, REP_DIV, PPSR_ROLE,
                   PPSL_DT, BILL_NM 등)
        count: 반환된 건수
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
    page_size: int = 50,
) -> dict[str, Any]:
    """
    특정 법안에 대한 국회의원 개인별 본회의 표결 기록을 조회합니다.

    Get individual member voting records for a specific bill (per-member yes/no/abstain).
    Unlike get_vote_results (aggregate counts), this returns one row per member.

    Args:
        bill_id: 의안ID — 필수. search_bills 결과의 BILL_ID (예: "PRC_T2M6W0F2...").
                 BILL_NO(숫자)가 아닌 BILL_ID(PRC_...)를 사용해야 합니다.
        age: 대수 — 필수 (예: "22")
        member_name: 의원명 필터 (선택, 예: "홍길동")
        party: 정당명 필터 (선택, 예: "더불어민주당")
        vote_result: 표결결과 필터 (선택) — "찬성" | "반대" | "기권"
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 50 — 본회의 의원 수가 ~300명이므로 50~100 권장)

    Returns:
        votes: 의원별 표결 목록 (HG_NM, POLY_NM, ORIG_NM, RESULT_VOTE_MOD,
               VOTE_DATE, BILL_NO, BILL_NAME, SESSION_CD, MONA_CD 등)
        count: 반환된 건수
        total_count: 전체 표결 의원 수
        has_more: 다음 페이지 존재 여부
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
                else "표결 기록이 없습니다. BILL_ID와 AGE를 확인하세요."
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

    Get members of a National Assembly committee.
    Uses the member info API filtered by committee name.

    Args:
        age: 대수 (기본값: "22", "16"~"22" 지원)
        committee: 위원회명 (선택, 예: "법제사법위원회", "국토교통위원회")
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과수 (기본값: 50)

    Returns:
        members: 위원 목록 (HG_NM, POLY_NM, ORIG_NM, CMIT_NM, REELE_GBN_NM 등)
        count: 반환된 건수
        total_count: 전체 건수
        has_more: 다음 페이지 존재 여부
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
