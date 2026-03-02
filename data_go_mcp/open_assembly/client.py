"""API client for Korean National Assembly Open API (open.assembly.go.kr)."""

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# Confirmed endpoint codes (verified 2026-02/03)
EP_BILLS = "nzmimeepazxkubdpn"              # 국회의원 발의법률안
EP_BILL_DETAIL = "ALLBILL"                  # 의안정보 통합 API
EP_BILL_REVIEW = "nwbpacrgavhjryiph"        # 의안 처리·심사정보
EP_MEMBER = "nwvrqwxyaytdsfvhu"             # 국회의원 정보 통합 API
EP_VOTE = "ncocpgfiaoituanbr"               # 의안별 표결현황
EP_BILL_PROPOSERS = "BILLINFOPPSR"          # 의안 제안자정보 (requires BILL_ID)
EP_MEMBER_VOTES = "nojepdqqaweusdfbi"       # 국회의원 본회의 표결정보 (requires BILL_ID + AGE)
EP_PENDING_BILLS = "nwbqublzajtcqpdae"      # 계류의안 (미처리 현안 목록)
EP_PLENARY_AGENDA = "nayjnliqaexiioauy"     # 본회의부의안건 (다음 본회의 상정 예정 안건)
EP_COMMITTEE_REVIEW_MTG = "BILLJUDGECONF"  # 위원회 심사 회의정보 (requires BILL_ID)
# EP_COMMITTEE_MEMBERS reuses EP_MEMBER with CMIT_NM filter

# Not available as Open API (only file data): 회의록, 청원, 법률안 제안이유


class AssemblyAPIClient:
    """열린국회정보 Open API 클라이언트."""

    def __init__(self) -> None:
        self.api_key = os.getenv("ASSEMBLY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ASSEMBLY_API_KEY environment variable is required. "
                "Sign up at https://open.assembly.go.kr to get your API key."
            )
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "AssemblyAPIClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.client.aclose()

    def _base_params(self) -> dict[str, Any]:
        return {"KEY": self.api_key, "Type": "json"}

    def _parse_response(self, data: dict, endpoint: str) -> tuple[list[dict], int]:
        """열린국회 API 응답 파싱. INFO-200 = 빈 결과, INFO-000 = 정상.

        Returns:
            (rows, total_count): 결과 행 목록과 총 건수.
        """
        body = data.get(endpoint, [])
        if not body:
            raise ValueError(f"Unexpected response structure for endpoint '{endpoint}'")

        head = body[0].get("head", [])
        total_count = int(head[0].get("list_total_count", 0)) if head else 0
        result = head[1].get("RESULT", {}) if len(head) > 1 else {}
        code = result.get("CODE", "")

        if code == "INFO-200":
            return [], 0
        if code != "INFO-000":
            msg = result.get("MESSAGE", "Unknown API error")
            raise ValueError(f"API error {code}: {msg}")

        rows = body[1].get("row", []) if len(body) > 1 else []
        # 단건이면 dict, 다건이면 list
        rows = rows if isinstance(rows, list) else [rows]
        return rows, total_count

    async def _get(self, endpoint: str, params: dict[str, Any]) -> tuple[list[dict], int]:
        """GET 요청 실행 및 응답 파싱."""
        merged = {**self._base_params(), **{k: v for k, v in params.items() if v is not None}}
        url = f"{BASE_URL}/{endpoint}"
        try:
            resp = await self.client.get(url, params=merged)
            resp.raise_for_status()
            return self._parse_response(resp.json(), endpoint)
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Request failed: {e}") from e

    # ------------------------------------------------------------------
    # P1: 핵심 Tool 메서드
    # ------------------------------------------------------------------

    async def search_bills(
        self,
        age: str,
        bill_name: Optional[str] = None,
        proposer: Optional[str] = None,
        proc_result: Optional[str] = None,
        committee: Optional[str] = None,
        propose_dt_from: Optional[str] = None,
        propose_dt_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """국회의원 발의법률안 목록 조회."""
        return await self._get(EP_BILLS, {
            "AGE": age,
            "BILL_NAME": bill_name,
            "PROPOSER": proposer,
            "PROC_RESULT": proc_result,
            "COMMITTEE": committee,
            "STR_DT": propose_dt_from,
            "END_DT": propose_dt_to,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_bill_detail(self, bill_no: str) -> tuple[list[dict], int]:
        """의안 상세정보 조회 (의안정보 통합 API)."""
        return await self._get(EP_BILL_DETAIL, {"BILL_NO": bill_no})

    async def get_member_info(
        self,
        unit_cd: str = "100022",
        name: Optional[str] = None,
        party: Optional[str] = None,
        district: Optional[str] = None,
        committee: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """국회의원 정보 조회."""
        return await self._get(EP_MEMBER, {
            "UNIT_CD": unit_cd,
            "HG_NM": name,
            "POLY_NM": party,
            "ORIG_NM": district,
            "CMIT_NM": committee,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_vote_results(
        self,
        age: str,
        bill_no: Optional[str] = None,
        bill_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """의안별 본회의 표결현황 조회."""
        return await self._get(EP_VOTE, {
            "AGE": age,
            "BILL_NO": bill_no,
            "BILL_NAME": bill_name,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_bill_review(
        self,
        age: str,
        bill_no: Optional[str] = None,
        committee: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """의안 처리·심사정보 조회 (위원회 및 본회의 처리 경로)."""
        return await self._get(EP_BILL_REVIEW, {
            "AGE": age,
            "BILL_NO": bill_no,
            "COMMITTEE_NM": committee,
            "pIndex": page,
            "pSize": page_size,
        })

    # ------------------------------------------------------------------
    # P2: 추가 Tool 메서드
    # ------------------------------------------------------------------

    async def get_bill_proposers(self, bill_id: str) -> tuple[list[dict], int]:
        """의안 제안자(공동발의자) 정보 조회. (BILLINFOPPSR)

        Args:
            bill_id: 의안ID (search_bills 결과의 BILL_ID, 예: PRC_Y2Z6X0...)
        """
        return await self._get(EP_BILL_PROPOSERS, {"BILL_ID": bill_id})

    async def get_member_votes(
        self,
        bill_id: str,
        age: str,
        member_name: Optional[str] = None,
        party: Optional[str] = None,
        vote_result: Optional[str] = None,
        page: int = 1,
        page_size: int = 300,
    ) -> tuple[list[dict], int]:
        """국회의원 본회의 표결정보 조회. 특정 법안에 대한 의원별 찬반 기록.

        Args:
            bill_id: 의안ID — 필수 (search_bills 결과의 BILL_ID, 예: PRC_...)
            age: 대수 — 필수 (예: "22")
            member_name: 의원명 필터 (선택)
            party: 정당명 필터 (선택)
            vote_result: 표결결과 필터 — "찬성" | "반대" | "기권" (선택)
        """
        return await self._get(EP_MEMBER_VOTES, {
            "BILL_ID": bill_id,
            "AGE": age,
            "HG_NM": member_name,
            "POLY_NM": party,
            "RESULT_VOTE_MOD": vote_result,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_committee_members(
        self,
        unit_cd: str = "100022",
        committee: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """위원회 위원 명단 조회. 국회의원 정보 API(EP_MEMBER)에 위원회 필터 적용."""
        return await self._get(EP_MEMBER, {
            "UNIT_CD": unit_cd,
            "CMIT_NM": committee,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_pending_bills(
        self,
        age: str,
        bill_name: Optional[str] = None,
        committee: Optional[str] = None,
        proposer: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """계류의안 목록 조회 — 아직 처리되지 않은 현안 법률안."""
        return await self._get(EP_PENDING_BILLS, {
            "AGE": age,
            "BILL_NAME": bill_name,
            "COMMITTEE": committee,
            "PROPOSER": proposer,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_plenary_agenda(
        self,
        age: str,
        session: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """본회의 부의안건 조회 — 본회의 상정 예정 안건 목록."""
        return await self._get(EP_PLENARY_AGENDA, {
            "AGE": age,
            "SESS_NO": session,
            "pIndex": page,
            "pSize": page_size,
        })

    async def get_bill_committee_review(
        self,
        bill_id: str,
    ) -> tuple[list[dict], int]:
        """의안 위원회 심사 회의정보 조회 — 특정 의안이 심사된 위원회 회의 목록."""
        return await self._get(EP_COMMITTEE_REVIEW_MTG, {"BILL_ID": bill_id})
