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
EP_MEMBER = "nwvrqwxyaytdsfvhu"             # 국회의원 정보 통합 API (current assembly only!)
EP_ALLNAME = "ALLNAMEMBER"                  # 역대 국회의원 정보 (all assemblies, correct data)
EP_VOTE = "ncocpgfiaoituanbr"               # 의안별 표결현황
EP_BILL_PROPOSERS = "BILLINFOPPSR"          # 의안 제안자정보 (requires BILL_ID)
EP_MEMBER_VOTES = "nojepdqqaweusdfbi"       # 국회의원 본회의 표결정보 (requires BILL_ID + AGE)
EP_PENDING_BILLS = "nwbqublzajtcqpdae"      # 계류의안 (미처리 현안 목록)
EP_PLENARY_AGENDA = "nayjnliqaexiioauy"     # 본회의부의안건 (다음 본회의 상정 예정 안건)
EP_COMMITTEE_REVIEW_MTG = "BILLJUDGECONF"  # 위원회 심사 회의정보 (requires BILL_ID)

# Not available as Open API (only file data): 회의록, 청원, 법률안 제안이유

# Assembly age label for ALLNAMEMBER (e.g., "22" -> "제22대")
_AGE_LABEL = {str(i): f"제{i}대" for i in range(1, 30)}


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
        # Some endpoints return {"RESULT": {"CODE": "INFO-200", ...}} when no data,
        # instead of the normal {"endpoint_name": [{head}, {row}]} structure.
        if "RESULT" in data and endpoint not in data:
            code = data["RESULT"].get("CODE", "")
            if code == "INFO-200":
                return [], 0
            msg = data["RESULT"].get("MESSAGE", "Unknown API error")
            raise ValueError(f"API error {code}: {msg}")

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
        except httpx.TimeoutException as e:
            raise ValueError(f"Request timed out after 30s — API may be slow, try again: {e}") from e
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
        """국회의원 발의법률안 목록 조회.

        NOTE: This endpoint uses "COMMITTEE" (not "COMMITTEE_NM") for committee filter.
        get_bill_review uses "COMMITTEE_NM" -- this is an API-level inconsistency.
        NOTE: The API does NOT support date range filtering natively. When
        propose_dt_from/propose_dt_to are provided, results are fetched in bulk
        and filtered client-side (scans up to 2,000 results).
        """
        if not propose_dt_from and not propose_dt_to:
            return await self._get(EP_BILLS, {
                "AGE": age,
                "BILL_NAME": bill_name,
                "PROPOSER": proposer,
                "PROC_RESULT": proc_result,
                "COMMITTEE": committee,
                "pIndex": page,
                "pSize": page_size,
            })

        # Client-side date filtering -- API ignores date params
        all_rows: list[dict] = []
        p = 1
        while p <= 20:
            rows, total = await self._get(EP_BILLS, {
                "AGE": age,
                "BILL_NAME": bill_name,
                "PROPOSER": proposer,
                "PROC_RESULT": proc_result,
                "COMMITTEE": committee,
                "pIndex": p,
                "pSize": 100,
            })
            if not rows:
                break
            all_rows.extend(rows)
            if len(all_rows) >= total:
                break
            p += 1

        if propose_dt_from:
            all_rows = [r for r in all_rows if (r.get("PROPOSE_DT") or "") >= propose_dt_from]
        if propose_dt_to:
            all_rows = [r for r in all_rows if (r.get("PROPOSE_DT") or "") <= propose_dt_to]

        total_filtered = len(all_rows)
        start = (page - 1) * page_size
        end = start + page_size
        return all_rows[start:end], total_filtered

    async def get_bill_detail(self, bill_no: str) -> tuple[list[dict], int]:
        """의안 상세정보 조회 (의안정보 통합 API)."""
        return await self._get(EP_BILL_DETAIL, {"BILL_NO": bill_no})

    def _parse_allname_for_age(self, rows: list[dict], age: str) -> list[dict]:
        """Parse ALLNAMEMBER rows and extract per-assembly data.

        ALLNAMEMBER returns one row per MP with slash-separated fields for
        multi-term members (e.g., party="새누리당/자유한국당" for 2 terms).
        This method extracts the data for a specific assembly.
        """
        age_label = _AGE_LABEL.get(age, f"제{age}대")
        slash_fields = {
            "PLPT_NM": "POLY_NM",
            "ELECD_NM": "ORIG_NM",
            "ELECD_DIV_NM": "ELECT_GBN_NM",
            "BLNG_CMIT_NM": "CMIT_NM",
        }
        result = []
        for r in rows:
            era_str = r.get("GTELT_ERACO") or ""
            eras = [e.strip() for e in era_str.split(", ") if e.strip()]
            if age_label not in eras:
                continue
            idx = eras.index(age_label)
            n_eras = len(eras)

            mapped: dict[str, Any] = {
                "MONA_CD": r.get("NAAS_CD"),
                "HG_NM": r.get("NAAS_NM"),
                "HJ_NM": r.get("NAAS_CH_NM"),
                "ENG_NM": r.get("NAAS_EN_NM"),
                "SEX_GBN_NM": r.get("NTR_DIV"),
                "BTH_DATE": r.get("BIRDY_DT"),
                "REELE_GBN_NM": r.get("RLCT_DIV_NM"),
                "E_MAIL": r.get("NAAS_EMAIL_ADDR"),
                "HOMEPAGE": r.get("NAAS_HP_URL"),
                "NAAS_PIC": r.get("NAAS_PIC"),
            }
            for src, dst in slash_fields.items():
                val = r.get(src) or ""
                parts = val.split("/")
                if len(parts) == n_eras:
                    mapped[dst] = parts[idx].strip()
                elif len(parts) == 1:
                    mapped[dst] = parts[0].strip()
                else:
                    mapped[dst] = parts[min(idx, len(parts) - 1)].strip() if parts else ""
            result.append(mapped)
        return result

    async def get_member_info(
        self,
        unit_cd: str = "100022",
        age: Optional[str] = None,
        name: Optional[str] = None,
        party: Optional[str] = None,
        district: Optional[str] = None,
        committee: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """국회의원 정보 조회.

        Uses ALLNAMEMBER endpoint to provide correct per-assembly data.
        The EP_MEMBER endpoint (nwvrqwxyaytdsfvhu) ignores UNIT_CD and always
        returns current-assembly data, which is incorrect for historical queries.
        """
        if age is None:
            age = unit_cd.replace("100", "").lstrip("0") if unit_cd.startswith("100") else "22"

        # If name is given, ALLNAMEMBER supports NAAS_NM filter (efficient)
        params: dict[str, Any] = {"pIndex": 1, "pSize": 100}
        if name:
            params["NAAS_NM"] = name

        all_rows: list[dict] = []
        p = 1
        while True:
            params["pIndex"] = p
            rows, total = await self._get(EP_ALLNAME, params)
            if not rows:
                break
            all_rows.extend(rows)
            if len(all_rows) >= total:
                break
            p += 1

        # Parse and filter for the requested assembly
        parsed = self._parse_allname_for_age(all_rows, age)

        # Apply client-side filters
        if party:
            parsed = [r for r in parsed if party in (r.get("POLY_NM") or "")]
        if district:
            parsed = [r for r in parsed if district in (r.get("ORIG_NM") or "")]
        if committee:
            parsed = [r for r in parsed if committee in (r.get("CMIT_NM") or "")]

        total_filtered = len(parsed)
        start = (page - 1) * page_size
        end = start + page_size
        return parsed[start:end], total_filtered

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
        """위원회 위원 명단 조회. ALLNAMEMBER 기반으로 정확한 역대 데이터 제공."""
        age = unit_cd.replace("100", "").lstrip("0") if unit_cd.startswith("100") else "22"
        return await self.get_member_info(
            age=age,
            committee=committee,
            page=page,
            page_size=page_size,
        )

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
