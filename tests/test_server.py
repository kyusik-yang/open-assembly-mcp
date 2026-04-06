"""Integration-style tests for MCP server tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("ASSEMBLY_API_KEY", "test-api-key-1234")


def _make_mock_client(rows: list, method: str, total: int | None = None):
    """AssemblyAPIClient의 특정 메서드를 mock으로 대체하는 헬퍼.

    Client methods now return (rows, total_count) tuples.
    """
    mock_client = AsyncMock()
    t = total if total is not None else len(rows)
    getattr(mock_client, method).return_value = (rows, t)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestSearchBillsTool:
    @pytest.mark.asyncio
    async def test_returns_bills_on_success(self):
        from data_go_mcp.open_assembly.server import search_bills

        sample_rows = [{"BILL_NO": "2200001", "BILL_NAME": "테스트법률안", "RST_PROPOSER": "홍길동"}]
        mock_client = _make_mock_client(sample_rows, "search_bills", total=42)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_bills(assembly="22", bill_name="테스트")

        assert result["count"] == 1
        assert result["total_count"] == 42
        assert result["has_more"] is True
        assert result["bills"][0]["BILL_NO"] == "2200001"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_has_more_false_when_last_page(self):
        from data_go_mcp.open_assembly.server import search_bills

        sample_rows = [{"BILL_NO": "2200001"}]
        # total=1, page=1, page_size=10 → has_more = 1 > 10 = False
        mock_client = _make_mock_client(sample_rows, "search_bills", total=1)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_bills(assembly="22")

        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self):
        from data_go_mcp.open_assembly.server import search_bills

        mock_client = _make_mock_client([], "search_bills", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_bills(assembly="22", bill_name="존재하지않음")

        assert result["count"] == 0
        assert result["total_count"] == 0
        assert result["has_more"] is False
        assert result["bills"] == []

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self):
        from data_go_mcp.open_assembly.server import search_bills

        mock_client = AsyncMock()
        mock_client.search_bills.side_effect = ValueError("API error ERROR-290: 인증키 오류")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_bills(assembly="22")

        assert "error" in result
        assert result["bills"] == []

    @pytest.mark.asyncio
    async def test_date_filter_passed_to_client(self):
        from data_go_mcp.open_assembly.server import search_bills

        sample_rows = [
            {"BILL_NO": "2200001", "BILL_NAME": "테스트", "PROPOSE_DT": "2025-06-15"},
        ]
        mock_client = _make_mock_client(sample_rows, "search_bills", total=1)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_bills(
                assembly="22", propose_dt_from="2025-01-01", propose_dt_to="2025-12-31"
            )

        call_kwargs = mock_client.search_bills.call_args.kwargs
        assert call_kwargs["propose_dt_from"] == "2025-01-01"
        assert call_kwargs["propose_dt_to"] == "2025-12-31"


class TestGetBillDetailTool:
    @pytest.mark.asyncio
    async def test_returns_bill_on_found(self):
        from data_go_mcp.open_assembly.server import get_bill_detail

        sample_bill = {"BILL_NO": "2200001", "BILL_NM": "테스트법률안", "PPSR_NM": "홍길동"}
        mock_client = _make_mock_client([sample_bill], "get_bill_detail")

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_detail(bill_no="2200001")

        assert result["bill"]["BILL_NO"] == "2200001"

    @pytest.mark.asyncio
    async def test_returns_none_on_not_found(self):
        from data_go_mcp.open_assembly.server import get_bill_detail

        mock_client = _make_mock_client([], "get_bill_detail", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_detail(bill_no="9999999")

        assert result["bill"] is None


class TestGetMemberInfoTool:
    @pytest.mark.asyncio
    async def test_returns_members(self):
        from data_go_mcp.open_assembly.server import get_member_info

        sample_rows = [{"HG_NM": "홍길동", "POLY_NM": "더불어민주당", "CMIT_NM": "법제사법위원회"}]
        mock_client = _make_mock_client(sample_rows, "get_member_info", total=5)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_member_info(assembly="22", name="홍길동")

        assert result["count"] == 1
        assert result["total_count"] == 5
        assert result["members"][0]["HG_NM"] == "홍길동"

    @pytest.mark.asyncio
    async def test_assembly_passed_to_client(self):
        """age가 client.get_member_info에 올바르게 전달되는지 확인."""
        from data_go_mcp.open_assembly.server import get_member_info

        mock_client = _make_mock_client([], "get_member_info")

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_member_info(assembly="22")

        assert mock_client.get_member_info.call_args.kwargs["age"] == "22"

    @pytest.mark.asyncio
    async def test_assembly_16_passed_to_client(self):
        """16대 age가 올바르게 전달되는지 확인."""
        from data_go_mcp.open_assembly.server import get_member_info

        mock_client = _make_mock_client([], "get_member_info")

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_member_info(assembly="16")

        assert mock_client.get_member_info.call_args.kwargs["age"] == "16"


class TestGetBillProposersTool:
    @pytest.mark.asyncio
    async def test_returns_proposers_by_bill_id(self):
        from data_go_mcp.open_assembly.server import get_bill_proposers

        sample_rows = [
            {"PPSR_NM": "홍길동", "PPSR_POLY_NM": "더불어민주당", "REP_DIV": "대표발의", "PPSR_ROLE": "발의자"},
            {"PPSR_NM": "김철수", "PPSR_POLY_NM": "더불어민주당", "REP_DIV": "공동발의", "PPSR_ROLE": "발의자"},
        ]
        mock_client = _make_mock_client(sample_rows, "get_bill_proposers")

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_proposers(bill_id="PRC_Y2Z6X0Y2W1X9V1W1D4E4D3B7B8Z1A1")

        assert result["count"] == 2
        assert result["total_count"] == 2
        assert result["proposers"][0]["PPSR_NM"] == "홍길동"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_uses_bill_id_param(self):
        """BILLINFOPPSR는 BILL_ID 파라미터를 사용해야 함."""
        from data_go_mcp.open_assembly.server import get_bill_proposers

        mock_client = _make_mock_client([], "get_bill_proposers")

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_bill_proposers(bill_id="PRC_TEST123")

        assert mock_client.get_bill_proposers.call_args.kwargs["bill_id"] == "PRC_TEST123"


class TestGetCommitteeMembersTool:
    @pytest.mark.asyncio
    async def test_returns_committee_members(self):
        from data_go_mcp.open_assembly.server import get_committee_members

        sample_rows = [
            {"HG_NM": "홍길동", "POLY_NM": "더불어민주당", "CMIT_NM": "법제사법위원회"},
        ]
        mock_client = _make_mock_client(sample_rows, "get_committee_members", total=18)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_committee_members(assembly="22", committee="법제사법위원회")

        assert result["count"] == 1
        assert result["total_count"] == 18
        assert result["members"][0]["CMIT_NM"] == "법제사법위원회"


class TestGetVoteResultsTool:
    @pytest.mark.asyncio
    async def test_returns_vote_results(self):
        from data_go_mcp.open_assembly.server import get_vote_results

        sample_rows = [
            {
                "BILL_NO": "2200001",
                "BILL_NAME": "테스트법안",
                "MEMBER_TCNT": "300",
                "YES_TCNT": "200",
                "NO_TCNT": "80",
                "BLANK_TCNT": "20",
                "PROC_RESULT_CD": "원안가결",
            }
        ]
        mock_client = _make_mock_client(sample_rows, "get_vote_results", total=150)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_vote_results(assembly="22")

        assert result["count"] == 1
        assert result["total_count"] == 150
        assert result["votes"][0]["YES_TCNT"] == "200"


class TestGetMemberVotesTool:
    @pytest.mark.asyncio
    async def test_returns_per_member_votes(self):
        from data_go_mcp.open_assembly.server import get_member_votes

        sample_rows = [
            {"HG_NM": "홍길동", "POLY_NM": "더불어민주당", "ORIG_NM": "서울 강남갑", "RESULT_VOTE_MOD": "찬성"},
            {"HG_NM": "김철수", "POLY_NM": "국민의힘", "ORIG_NM": "부산 해운대갑", "RESULT_VOTE_MOD": "반대"},
        ]
        mock_client = _make_mock_client(sample_rows, "get_member_votes", total=295)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_member_votes(bill_id="PRC_T2M6W0F2I1W2T1X7T4K2Q5A9J4P2M5", assembly="22")

        assert result["count"] == 2
        assert result["total_count"] == 295
        assert result["votes"][0]["RESULT_VOTE_MOD"] == "찬성"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_requires_bill_id_and_age(self):
        """BILL_ID와 AGE 모두 클라이언트에 전달되는지 확인."""
        from data_go_mcp.open_assembly.server import get_member_votes

        mock_client = _make_mock_client([], "get_member_votes", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_member_votes(bill_id="PRC_TEST123", assembly="22")

        call_kwargs = mock_client.get_member_votes.call_args.kwargs
        assert call_kwargs["bill_id"] == "PRC_TEST123"
        assert call_kwargs["age"] == "22"

    @pytest.mark.asyncio
    async def test_vote_result_filter_passed(self):
        """찬성/반대/기권 필터가 전달되는지 확인."""
        from data_go_mcp.open_assembly.server import get_member_votes

        mock_client = _make_mock_client([], "get_member_votes", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_member_votes(bill_id="PRC_TEST", assembly="22", vote_result="찬성", party="더불어민주당")

        call_kwargs = mock_client.get_member_votes.call_args.kwargs
        assert call_kwargs["vote_result"] == "찬성"
        assert call_kwargs["party"] == "더불어민주당"


class TestGetBillReviewTool:
    @pytest.mark.asyncio
    async def test_returns_review_info(self):
        from data_go_mcp.open_assembly.server import get_bill_review

        sample_rows = [
            {"BILL_NO": "2200001", "BILL_NM": "테스트법안", "COMMITTEE_NM": "법제사법위원회"}
        ]
        mock_client = _make_mock_client(sample_rows, "get_bill_review", total=3)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_review(assembly="22", bill_no="2200001")

        assert result["count"] == 1
        assert result["total_count"] == 3
        assert result["reviews"][0]["COMMITTEE_NM"] == "법제사법위원회"


class TestGetPendingBillsTool:
    @pytest.mark.asyncio
    async def test_returns_pending_bills(self):
        from data_go_mcp.open_assembly.server import get_pending_bills

        sample_rows = [
            {"BILL_NO": "2217500", "BILL_NAME": "계류테스트법안", "PROPOSER": "홍길동", "COMMITTEE": "법제사법위원회"}
        ]
        mock_client = _make_mock_client(sample_rows, "get_pending_bills", total=8900)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_pending_bills(assembly="22")

        assert result["count"] == 1
        assert result["total_count"] == 8900
        assert result["has_more"] is True
        assert result["bills"][0]["BILL_NO"] == "2217500"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_filters_passed_to_client(self):
        from data_go_mcp.open_assembly.server import get_pending_bills

        mock_client = _make_mock_client([], "get_pending_bills", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_pending_bills(assembly="22", committee="법제사법위원회", proposer="홍길동")

        call_kwargs = mock_client.get_pending_bills.call_args.kwargs
        assert call_kwargs["committee"] == "법제사법위원회"
        assert call_kwargs["proposer"] == "홍길동"


class TestGetPlenaryAgendaTool:
    @pytest.mark.asyncio
    async def test_returns_agenda_items(self):
        from data_go_mcp.open_assembly.server import get_plenary_agenda

        sample_rows = [
            {"BILL_NO": "2217501", "BILL_NAME": "부의안건테스트법안", "SESS_NO": "1"}
        ]
        mock_client = _make_mock_client(sample_rows, "get_plenary_agenda", total=3)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_plenary_agenda(assembly="22")

        assert result["count"] == 1
        assert result["total_count"] == 3
        assert result["agenda_items"][0]["BILL_NO"] == "2217501"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_session_filter_passed(self):
        from data_go_mcp.open_assembly.server import get_plenary_agenda

        mock_client = _make_mock_client([], "get_plenary_agenda", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_plenary_agenda(assembly="22", session="2")

        assert mock_client.get_plenary_agenda.call_args.kwargs["session"] == "2"


class TestGetBillCommitteeReviewTool:
    @pytest.mark.asyncio
    async def test_returns_committee_meetings(self):
        from data_go_mcp.open_assembly.server import get_bill_committee_review

        sample_rows = [
            {"BILL_ID": "PRC_TEST123", "CMIT_NM": "법제사법위원회", "MTG_DT": "20240315"}
        ]
        mock_client = _make_mock_client(sample_rows, "get_bill_committee_review", total=2)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_committee_review(bill_id="PRC_TEST123")

        assert result["count"] == 1
        assert result["total_count"] == 2
        assert result["meetings"][0]["CMIT_NM"] == "법제사법위원회"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_handles_no_meetings(self):
        from data_go_mcp.open_assembly.server import get_bill_committee_review

        mock_client = _make_mock_client([], "get_bill_committee_review", total=0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_committee_review(bill_id="PRC_NOTFOUND")

        assert result["count"] == 0
        assert result["meetings"] == []
        assert "BILL_ID" in result["message"]


class TestGetBillSummaryTool:
    @pytest.mark.asyncio
    async def test_chains_four_calls_successfully(self):
        """get_bill_summary가 detail + review + proposers + meetings를 취합하는지 확인."""
        from data_go_mcp.open_assembly.server import get_bill_summary

        detail_row = {"BILL_NO": "2216983", "BILL_NM": "테스트법안", "LINK_URL": "https://example.com"}
        review_row = {"BILL_ID": "PRC_TEST123", "BILL_NM": "테스트법안", "COMMITTEE_NM": "법제사법위원회"}
        proposer_rows = [{"PPSR_NM": "홍길동", "PPSR_POLY_NM": "민주당"}]
        meeting_rows = [{"CMIT_NM": "법제사법위원회", "MTG_DT": "20240315"}]

        mock_client = AsyncMock()
        mock_client.get_bill_detail.return_value = ([detail_row], 1)
        mock_client.get_bill_review.return_value = ([review_row], 1)
        mock_client.get_bill_proposers.return_value = (proposer_rows, 1)
        mock_client.get_bill_committee_review.return_value = (meeting_rows, 1)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_summary(assembly="22", bill_no="2216983")

        assert result["bill_no"] == "2216983"
        assert result["detail"]["BILL_NO"] == "2216983"
        assert result["review"]["BILL_ID"] == "PRC_TEST123"
        assert len(result["proposers"]) == 1
        assert len(result["committee_meetings"]) == 1
        assert result["errors"] == {}
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_partial_failure_returns_errors_dict(self):
        """서브 호출 일부 실패 시 errors 딕셔너리에 기록되는지 확인."""
        from data_go_mcp.open_assembly.server import get_bill_summary

        review_row = {"BILL_ID": "PRC_TEST123", "BILL_NM": "테스트법안"}

        mock_client = AsyncMock()
        mock_client.get_bill_detail.side_effect = ValueError("API error")
        mock_client.get_bill_review.return_value = ([review_row], 1)
        mock_client.get_bill_proposers.return_value = ([], 0)
        mock_client.get_bill_committee_review.return_value = ([], 0)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_summary(assembly="22", bill_no="9999999")

        assert "detail" in result["errors"]
        assert result["detail"] is None
        assert result["review"] is not None

    @pytest.mark.asyncio
    async def test_no_bill_id_from_review_skips_dependent_calls(self):
        """review에서 BILL_ID를 얻지 못하면 proposers/meetings 호출이 스킵되는지 확인."""
        from data_go_mcp.open_assembly.server import get_bill_summary

        mock_client = AsyncMock()
        mock_client.get_bill_detail.return_value = ([], 0)
        mock_client.get_bill_review.return_value = ([], 0)  # no rows = no BILL_ID
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_bill_summary(assembly="22", bill_no="0000000")

        # proposers and committee_meetings calls should not have been made
        mock_client.get_bill_proposers.assert_not_called()
        mock_client.get_bill_committee_review.assert_not_called()
        assert "proposers" in result["errors"]
        assert "committee_meetings" in result["errors"]


def _make_phase3_mock(rows: list, total: int, raw=None):
    """Phase 3 툴용 mock: query_endpoint 반환값 설정."""
    mock_client = AsyncMock()
    mock_client.query_endpoint.return_value = (rows, total, raw)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestSearchNarsReportsTool:
    @pytest.mark.asyncio
    async def test_returns_reports_on_success(self):
        from data_go_mcp.open_assembly.server import search_nars_reports

        sample_rows = [
            {"TITL_NM": "인공지능 규제 동향", "PUBLG_DT": "20240601"},
            {"TITL_NM": "디지털플랫폼 규제", "PUBLG_DT": "20240915"},
        ]
        mock_client = _make_phase3_mock(sample_rows, 25)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_nars_reports(keyword="인공지능")

        assert result["count"] == 2
        assert result["total_count"] == 25
        assert result["has_more"] is True
        assert result["raw_response"] is None
        assert result["reports"][0]["TITL_NM"] == "인공지능 규제 동향"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_passes_keyword_as_titl_nm(self):
        from data_go_mcp.open_assembly.server import search_nars_reports

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_nars_reports(keyword="복지", date_from="20240101", date_to="20241231")

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert call_params["TITL_NM"] == "복지"
        assert call_params["PUBLG_STRT_DT"] == "20240101"
        assert call_params["PUBLG_END_DT"] == "20241231"

    @pytest.mark.asyncio
    async def test_no_keyword_omits_titl_nm(self):
        from data_go_mcp.open_assembly.server import search_nars_reports

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_nars_reports()

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert "TITL_NM" not in call_params

    @pytest.mark.asyncio
    async def test_uses_correct_endpoint_code(self):
        from data_go_mcp.open_assembly.server import search_nars_reports
        from data_go_mcp.open_assembly.client import EP_NARS_REPORTS

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_nars_reports(keyword="test")

        call_endpoint = mock_client.query_endpoint.call_args[0][0]
        assert call_endpoint == EP_NARS_REPORTS

    @pytest.mark.asyncio
    async def test_handles_raw_response(self):
        from data_go_mcp.open_assembly.server import search_nars_reports

        raw_data = {"unknown_structure": [1, 2, 3]}
        mock_client = _make_phase3_mock([], 0, raw=raw_data)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_nars_reports()

        assert result["raw_response"] == raw_data
        assert result["reports"] == []
        assert "비표준" in result["message"]

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from data_go_mcp.open_assembly.server import search_nars_reports

        mock_client = AsyncMock()
        mock_client.query_endpoint.side_effect = ValueError("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_nars_reports(keyword="test")

        assert "error" in result
        assert result["reports"] == []


class TestSearchPetitionsTool:
    @pytest.mark.asyncio
    async def test_pending_only_uses_pending_endpoint(self):
        from data_go_mcp.open_assembly.server import search_petitions
        from data_go_mcp.open_assembly.client import EP_PETITION_PENDING

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_petitions(assembly="22", include_closed=False)

        call_endpoint = mock_client.query_endpoint.call_args[0][0]
        assert call_endpoint == EP_PETITION_PENDING
        assert result["endpoint_used"] == EP_PETITION_PENDING

    @pytest.mark.asyncio
    async def test_include_closed_uses_list_endpoint(self):
        from data_go_mcp.open_assembly.server import search_petitions
        from data_go_mcp.open_assembly.client import EP_PETITION_LIST

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_petitions(assembly="22", include_closed=True)

        call_endpoint = mock_client.query_endpoint.call_args[0][0]
        assert call_endpoint == EP_PETITION_LIST
        assert result["endpoint_used"] == EP_PETITION_LIST

    @pytest.mark.asyncio
    async def test_returns_petitions_on_success(self):
        from data_go_mcp.open_assembly.server import search_petitions

        sample_rows = [
            {"PTTI_NM": "교육법 개정 청원", "PROPOSER": "시민A"},
            {"PTTI_NM": "환경보호 청원", "PROPOSER": "시민B"},
        ]
        mock_client = _make_phase3_mock(sample_rows, 2)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_petitions(assembly="22")

        assert result["count"] == 2
        assert result["total_count"] == 2
        assert result["has_more"] is False
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_passes_age_and_keyword(self):
        from data_go_mcp.open_assembly.server import search_petitions

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_petitions(assembly="21", keyword="교육", include_closed=False)

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert call_params["AGE"] == "21"
        assert call_params["PTTI_NM"] == "교육"

    @pytest.mark.asyncio
    async def test_handles_raw_response(self):
        from data_go_mcp.open_assembly.server import search_petitions

        mock_client = _make_phase3_mock([], 0, raw={"other": "format"})

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_petitions(assembly="22")

        assert result["raw_response"] is not None
        assert result["petitions"] == []

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from data_go_mcp.open_assembly.server import search_petitions

        mock_client = AsyncMock()
        mock_client.query_endpoint.side_effect = ValueError("API error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_petitions(assembly="22")

        assert "error" in result
        assert result["petitions"] == []


class TestGetScheduleTool:
    @pytest.mark.asyncio
    async def test_default_uses_all_endpoint(self):
        from data_go_mcp.open_assembly.server import get_schedule
        from data_go_mcp.open_assembly.client import EP_SCHEDULE_ALL

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(assembly="22")

        assert result["endpoint_used"] == EP_SCHEDULE_ALL
        assert result["schedule_type"] == "all"

    @pytest.mark.asyncio
    async def test_plenary_type_uses_plenary_endpoint(self):
        from data_go_mcp.open_assembly.server import get_schedule
        from data_go_mcp.open_assembly.client import EP_SCHEDULE_PLENARY

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(assembly="22", schedule_type="plenary")

        assert result["endpoint_used"] == EP_SCHEDULE_PLENARY
        assert result["schedule_type"] == "plenary"

    @pytest.mark.asyncio
    async def test_committee_type_passes_cmit_nm(self):
        from data_go_mcp.open_assembly.server import get_schedule
        from data_go_mcp.open_assembly.client import EP_SCHEDULE_COMMITTEE

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(
                assembly="22", schedule_type="committee", committee="법제사법위원회"
            )

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert call_params["CMIT_NM"] == "법제사법위원회"
        assert result["endpoint_used"] == EP_SCHEDULE_COMMITTEE

    @pytest.mark.asyncio
    async def test_committee_filter_ignored_for_non_committee_type(self):
        from data_go_mcp.open_assembly.server import get_schedule

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await get_schedule(assembly="22", schedule_type="plenary", committee="법사위")

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert "CMIT_NM" not in call_params

    @pytest.mark.asyncio
    async def test_returns_schedule_items_on_success(self):
        from data_go_mcp.open_assembly.server import get_schedule

        sample_rows = [
            {"CONF_DT": "20250301", "CONF_NM": "제1차 본회의"},
            {"CONF_DT": "20250315", "CONF_NM": "제2차 본회의"},
        ]
        mock_client = _make_phase3_mock(sample_rows, 100)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(assembly="22")

        assert result["count"] == 2
        assert result["total_count"] == 100
        assert result["has_more"] is True
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_schedule_type_case_insensitive(self):
        from data_go_mcp.open_assembly.server import get_schedule
        from data_go_mcp.open_assembly.client import EP_SCHEDULE_PLENARY

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(assembly="22", schedule_type="PLENARY")

        assert result["endpoint_used"] == EP_SCHEDULE_PLENARY

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from data_go_mcp.open_assembly.server import get_schedule

        mock_client = AsyncMock()
        mock_client.query_endpoint.side_effect = ValueError("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_schedule(assembly="22")

        assert "error" in result
        assert result["schedule_items"] == []


class TestSearchHearingsTool:
    @pytest.mark.asyncio
    async def test_confirmation_uses_confirm_endpoint(self):
        from data_go_mcp.open_assembly.server import search_hearings
        from data_go_mcp.open_assembly.client import EP_HEARING_CONFIRM

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_hearings(assembly="22", hearing_type="confirmation")

        assert result["endpoint_used"] == EP_HEARING_CONFIRM
        assert result["hearing_type"] == "confirmation"

    @pytest.mark.asyncio
    async def test_public_uses_public_endpoint(self):
        from data_go_mcp.open_assembly.server import search_hearings
        from data_go_mcp.open_assembly.client import EP_HEARING_PUBLIC

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_hearings(assembly="22", hearing_type="public")

        assert result["endpoint_used"] == EP_HEARING_PUBLIC
        assert result["hearing_type"] == "public"

    @pytest.mark.asyncio
    async def test_nominee_name_passed_as_naas_nm(self):
        from data_go_mcp.open_assembly.server import search_hearings

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_hearings(assembly="22", nominee_name="홍길동")

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert call_params["NAAS_NM"] == "홍길동"

    @pytest.mark.asyncio
    async def test_committee_filter_passed(self):
        from data_go_mcp.open_assembly.server import search_hearings

        mock_client = _make_phase3_mock([], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await search_hearings(assembly="22", committee="법제사법위원회")

        call_params = mock_client.query_endpoint.call_args[0][1]
        assert call_params["CMIT_NM"] == "법제사법위원회"

    @pytest.mark.asyncio
    async def test_returns_hearings_on_success(self):
        from data_go_mcp.open_assembly.server import search_hearings

        sample_rows = [
            {"CONF_DT": "20240901", "NAAS_NM": "홍길동", "CMIT_NM": "인사청문위원회"},
        ]
        mock_client = _make_phase3_mock(sample_rows, 50)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_hearings(assembly="22")

        assert result["count"] == 1
        assert result["total_count"] == 50
        assert result["has_more"] is True
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_handles_raw_response(self):
        from data_go_mcp.open_assembly.server import search_hearings

        mock_client = _make_phase3_mock([], 0, raw={"nonstandard": True})

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_hearings(assembly="22")

        assert result["raw_response"] is not None
        assert result["hearings"] == []

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from data_go_mcp.open_assembly.server import search_hearings

        mock_client = AsyncMock()
        mock_client.query_endpoint.side_effect = ValueError("HTTP 403")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await search_hearings(assembly="22")

        assert "error" in result
        assert result["hearings"] == []


class TestAnalyzeLegislatorTool:
    def _make_multi_mock(
        self,
        member_rows: list,
        member_total: int,
        bills_rows: list,
        bills_total: int,
    ):
        """analyze_legislator용 mock: get_member_info + search_bills 두 메서드 설정."""
        mock_client = AsyncMock()
        mock_client.get_member_info.return_value = (member_rows, member_total)
        # search_bills는 여러 번 호출될 수 있음 (페이지네이션)
        mock_client.search_bills.return_value = (bills_rows, bills_total)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest.mark.asyncio
    async def test_returns_member_and_bills_on_success(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_row = {
            "HG_NM": "이준석", "POLY_NM": "개혁신당", "ORIG_NM": "경기 화성시을",
            "CMIT_NM": "과학기술정보방송통신위원회", "REELE_GBN_NM": "초선",
        }
        bill_rows = [
            {"BILL_NO": "2200001", "BILL_NAME": "법안1", "RST_PROPOSER": "이준석",
             "PROPOSE_DT": "20250301", "PROC_RESULT": None, "COMMITTEE": "과기위"},
            {"BILL_NO": "2200002", "BILL_NAME": "법안2", "RST_PROPOSER": "이준석",
             "PROPOSE_DT": "20240601", "PROC_RESULT": "대안반영폐기", "COMMITTEE": "과기위"},
        ]
        mock_client = self._make_multi_mock([member_row], 1, bill_rows, 2)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="이준석", assembly="22")

        assert result["member"]["HG_NM"] == "이준석"
        assert result["bills"]["total"] == 2
        assert result["bills"]["retrieved"] == 2
        assert "error" not in result
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_bill_stats_computed_correctly(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_row = {"HG_NM": "홍길동", "POLY_NM": "민주당", "ORIG_NM": "서울 강남갑"}
        bill_rows = [
            {"BILL_NO": "001", "PROC_RESULT": None, "COMMITTEE": "법사위",
             "PROPOSE_DT": "20240101", "BILL_NAME": "법안A"},
            {"BILL_NO": "002", "PROC_RESULT": "원안가결", "COMMITTEE": "법사위",
             "PROPOSE_DT": "20250601", "BILL_NAME": "법안B"},
            {"BILL_NO": "003", "PROC_RESULT": "대안반영폐기", "COMMITTEE": "과기위",
             "PROPOSE_DT": "20250901", "BILL_NAME": "법안C"},
            {"BILL_NO": "004", "PROC_RESULT": None, "COMMITTEE": "법사위",
             "PROPOSE_DT": "20260101", "BILL_NAME": "법안D"},
        ]
        mock_client = self._make_multi_mock([member_row], 1, bill_rows, 4)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="홍길동", assembly="22")

        bills = result["bills"]
        assert bills["by_result"]["계류"] == 2
        assert bills["by_result"]["원안가결"] == 1
        assert bills["by_result"]["대안반영폐기"] == 1
        assert bills["by_committee"]["법사위"] == 3
        assert bills["by_committee"]["과기위"] == 1
        assert bills["by_year"]["2024"] == 1
        assert bills["by_year"]["2025"] == 2
        assert bills["by_year"]["2026"] == 1

    @pytest.mark.asyncio
    async def test_recent_bills_are_most_recent_five(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_row = {"HG_NM": "홍길동", "POLY_NM": "민주당", "ORIG_NM": "서울"}
        # 6 bills with different dates
        bill_rows = [
            {"BILL_NO": f"200000{i}", "PROC_RESULT": None, "COMMITTEE": "법사위",
             "PROPOSE_DT": f"202{i}0101", "BILL_NAME": f"법안{i}"}
            for i in range(6)
        ]
        mock_client = self._make_multi_mock([member_row], 1, bill_rows, 6)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="홍길동")

        recent = result["bills"]["recent"]
        assert len(recent) == 5
        # Most recent first (2025, 2024, 2023, 2022, 2021 in descending order)
        dates = [r["PROPOSE_DT"] for r in recent]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_member_not_found_sets_error(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        mock_client = self._make_multi_mock([], 0, [], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="존재하지않는의원", assembly="22")

        assert "member" in result["errors"]
        assert result["member"] is None

    @pytest.mark.asyncio
    async def test_multiple_members_sets_ambiguous_note(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_rows = [
            {"HG_NM": "김철수", "POLY_NM": "민주당", "ORIG_NM": "서울"},
            {"HG_NM": "김철수", "POLY_NM": "국민의힘", "ORIG_NM": "부산"},
        ]
        mock_client = self._make_multi_mock(member_rows, 2, [], 0)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="김철수")

        assert "member_ambiguous" in result["errors"]
        assert result["member"] == member_rows[0]  # first match used
        assert len(result["member_all_matches"]) == 2

    @pytest.mark.asyncio
    async def test_member_api_error_still_returns_structure(self):
        from data_go_mcp.open_assembly.server import analyze_legislator

        mock_client = AsyncMock()
        mock_client.get_member_info.side_effect = ValueError("API timeout")
        mock_client.search_bills.return_value = ([], 0)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="홍길동")

        assert "member" in result["errors"]
        assert result["member"] is None
        assert "bills" in result  # bills key always present

    @pytest.mark.asyncio
    async def test_pagination_fetches_beyond_first_page(self):
        """총 150건일 때 2페이지까지 호출하는지 확인."""
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_row = {"HG_NM": "이준석", "POLY_NM": "개혁신당", "ORIG_NM": "경기"}
        # First page: 100 bills; second page: 50 bills
        page1_bills = [
            {"BILL_NO": f"{i}", "PROC_RESULT": None, "COMMITTEE": "과기위",
             "PROPOSE_DT": "20250101", "BILL_NAME": f"법안{i}"}
            for i in range(100)
        ]
        page2_bills = [
            {"BILL_NO": f"{i+100}", "PROC_RESULT": None, "COMMITTEE": "과기위",
             "PROPOSE_DT": "20240101", "BILL_NAME": f"법안{i+100}"}
            for i in range(50)
        ]

        mock_client = AsyncMock()
        mock_client.get_member_info.return_value = ([member_row], 1)
        # First call: 100 rows, total=150; second call: 50 rows
        mock_client.search_bills.side_effect = [
            (page1_bills, 150),
            (page2_bills, 150),
            ([], 150),  # safety: if called again
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="이준석")

        assert result["bills"]["total"] == 150
        assert result["bills"]["retrieved"] == 150
        assert mock_client.search_bills.call_count == 2

    @pytest.mark.asyncio
    async def test_iso_date_format_year_extraction(self):
        """PROPOSE_DT가 ISO 형식('2025-03-01')이어도 연도가 올바르게 추출되는지 확인."""
        from data_go_mcp.open_assembly.server import analyze_legislator

        member_row = {"HG_NM": "홍길동", "POLY_NM": "민주당", "ORIG_NM": "서울"}
        bill_rows = [
            {"BILL_NO": "001", "PROC_RESULT": None, "COMMITTEE": "법사위",
             "PROPOSE_DT": "2025-03-01", "BILL_NAME": "ISO포맷법안"},
        ]
        mock_client = self._make_multi_mock([member_row], 1, bill_rows, 1)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await analyze_legislator(name="홍길동")

        assert "2025" in result["bills"]["by_year"]
        assert result["bills"]["by_year"]["2025"] == 1


class TestGetPartyCohesionTool:
    def _make_vote_rows(self, party_votes: dict[str, list[str]]) -> list[dict]:
        """party_votes: {"민주당": ["찬성", "찬성", "반대"], ...} → vote rows."""
        rows = []
        for party, votes in party_votes.items():
            for i, vote in enumerate(votes):
                rows.append({
                    "HG_NM": f"{party[:2]}의원{i}",
                    "POLY_NM": party,
                    "ORIG_NM": f"선거구{i}",
                    "RESULT_VOTE_MOD": vote,
                    "MONA_CD": f"MONA{i}",
                })
        return rows

    @pytest.mark.asyncio
    async def test_returns_correct_aggregates(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({
            "더불어민주당": ["찬성"] * 10 + ["기권"],
            "국민의힘": ["반대"] * 5,
        })
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, len(vote_rows))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        assert result["overall"]["yes"] == 10
        assert result["overall"]["no"] == 5
        assert result["overall"]["abstain"] == 1
        assert result["total_voted"] == 16
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_rice_index_unanimous_party(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({"민주당": ["찬성"] * 10})
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, 10)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        party = result["by_party"]["민주당"]
        assert party["rice_index"] == 1.0
        assert party["unanimous"] is True
        assert party["dominant_position"] == "찬성"

    @pytest.mark.asyncio
    async def test_rice_index_perfectly_split(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({"개혁신당": ["찬성"] * 5 + ["반대"] * 5})
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, 10)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        party = result["by_party"]["개혁신당"]
        assert party["rice_index"] == 0.0
        assert party["unanimous"] is False

    @pytest.mark.asyncio
    async def test_rice_index_none_when_all_abstain(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({"무소속": ["기권"] * 3})
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, 3)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        party = result["by_party"]["무소속"]
        assert party["rice_index"] is None
        assert party["dominant_position"] is None
        # No dissenters when no dominant position
        assert result["dissenters"] == []

    @pytest.mark.asyncio
    async def test_dissenters_identified_correctly(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        # 민주당: 9 찬성, 1 반대 dissenter, 1 기권 abstainer
        vote_rows = self._make_vote_rows({
            "더불어민주당": ["찬성"] * 9 + ["반대", "기권"],
        })
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, len(vote_rows))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        dissenters = result["dissenters"]
        assert len(dissenters) == 2
        types = {d["type"] for d in dissenters}
        assert "opposite" in types
        assert "abstain" in types
        for d in dissenters:
            assert d["party"] == "더불어민주당"
            assert d["party_dominant"] == "찬성"

    @pytest.mark.asyncio
    async def test_no_dissenters_when_unanimous(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({"민주당": ["찬성"] * 10, "국민의힘": ["반대"] * 5})
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, 15)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        assert result["dissenters"] == []

    @pytest.mark.asyncio
    async def test_by_party_sorted_by_total_voted_descending(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        vote_rows = self._make_vote_rows({
            "소수당": ["찬성"] * 2,
            "대정당": ["찬성"] * 10,
            "중간당": ["반대"] * 5,
        })
        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = (vote_rows, len(vote_rows))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_TEST", assembly="22")

        parties = list(result["by_party"].keys())
        totals = [result["by_party"][p]["total_voted"] for p in parties]
        assert totals == sorted(totals, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_vote_records_returns_empty_result(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        mock_client = AsyncMock()
        mock_client.get_member_votes.return_value = ([], 0)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_NOTFOUND", assembly="22")

        assert result["total_voted"] == 0
        assert result["by_party"] == {}
        assert result["dissenters"] == []
        assert "BILL_ID" in result["message"]

    @pytest.mark.asyncio
    async def test_api_error_returns_error_key(self):
        from data_go_mcp.open_assembly.server import get_party_cohesion

        mock_client = AsyncMock()
        mock_client.get_member_votes.side_effect = ValueError("HTTP 403")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await get_party_cohesion(bill_id="PRC_BAD", assembly="22")

        assert "error" in result
        assert "HTTP 403" in result["error"]


class TestDiscoverApisTool:
    @pytest.mark.asyncio
    async def test_returns_all_entries_with_no_keyword(self):
        from data_go_mcp.open_assembly.server import discover_apis
        from data_go_mcp.open_assembly.registry import ENDPOINT_REGISTRY

        result = await discover_apis()

        assert result["count"] == len(ENDPOINT_REGISTRY)
        assert "by_category" in result
        assert "endpoints" in result
        assert "note" in result
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_keyword_filters_results(self):
        from data_go_mcp.open_assembly.server import discover_apis

        result = await discover_apis(keyword="bills")

        assert result["count"] > 0
        for ep in result["endpoints"]:
            searchable = " ".join([
                ep.get("code", ""),
                ep.get("name", ""),
                ep.get("name_en", ""),
                ep.get("category", ""),
                ep.get("notes", ""),
                ep.get("mcp_tool") or "",
            ]).lower()
            assert "bills" in searchable

    @pytest.mark.asyncio
    async def test_korean_keyword_matches(self):
        from data_go_mcp.open_assembly.server import discover_apis

        result = await discover_apis(keyword="표결")

        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_no_matches_returns_zero_count(self):
        from data_go_mcp.open_assembly.server import discover_apis

        result = await discover_apis(keyword="존재하지않는키워드xyz")

        assert result["count"] == 0
        assert result["endpoints"] == []

    @pytest.mark.asyncio
    async def test_by_category_groups_correctly(self):
        from data_go_mcp.open_assembly.server import discover_apis

        result = await discover_apis()

        by_cat = result["by_category"]
        assert "bills" in by_cat
        assert "members" in by_cat
        assert "votes" in by_cat
        # Each item in a category list must have a "code" field
        for cat, items in by_cat.items():
            for item in items:
                assert "code" in item

    @pytest.mark.asyncio
    async def test_mcp_tool_field_present(self):
        from data_go_mcp.open_assembly.server import discover_apis

        result = await discover_apis(keyword="search_bills")

        assert result["count"] >= 1
        bill_ep = next(
            (ep for ep in result["endpoints"] if ep.get("mcp_tool") == "search_bills"),
            None,
        )
        assert bill_ep is not None
        assert bill_ep["code"] == "nzmimeepazxkubdpn"


class TestQueryAssemblyTool:
    @pytest.mark.asyncio
    async def test_returns_rows_on_standard_response(self):
        from data_go_mcp.open_assembly.server import query_assembly

        sample_rows = [{"BILL_NO": "2200001", "BILL_NAME": "테스트"}]
        mock_client = AsyncMock()
        mock_client.query_endpoint.return_value = (sample_rows, 42, None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await query_assembly(
                endpoint_code="nzmimeepazxkubdpn",
                params={"AGE": "22"},
            )

        assert result["count"] == 1
        assert result["total_count"] == 42
        assert result["has_more"] is True
        assert result["raw_response"] is None
        assert result["endpoint"] == "nzmimeepazxkubdpn"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_returns_raw_on_nonstandard_response(self):
        from data_go_mcp.open_assembly.server import query_assembly

        raw_data = {"someKey": [{"value": 1}]}
        mock_client = AsyncMock()
        mock_client.query_endpoint.return_value = ([], 0, raw_data)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await query_assembly(endpoint_code="unknown_endpoint")

        assert result["rows"] == []
        assert result["count"] == 0
        assert result["raw_response"] == raw_data
        assert "비표준" in result["message"]
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from data_go_mcp.open_assembly.server import query_assembly

        mock_client = AsyncMock()
        mock_client.query_endpoint.side_effect = ValueError("HTTP 403: forbidden")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await query_assembly(endpoint_code="bad_code")

        assert "error" in result
        assert result["rows"] == []
        assert result["raw_response"] is None

    @pytest.mark.asyncio
    async def test_passes_page_params_to_client(self):
        from data_go_mcp.open_assembly.server import query_assembly

        mock_client = AsyncMock()
        mock_client.query_endpoint.return_value = ([], 0, None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            await query_assembly(
                endpoint_code="nzmimeepazxkubdpn",
                params={"AGE": "22"},
                page=3,
                page_size=50,
            )

        call_args = mock_client.query_endpoint.call_args
        passed_params = call_args[0][1]
        assert passed_params["pIndex"] == 3
        assert passed_params["pSize"] == 50
        assert passed_params["AGE"] == "22"

    @pytest.mark.asyncio
    async def test_no_results_returns_helpful_message(self):
        from data_go_mcp.open_assembly.server import query_assembly

        mock_client = AsyncMock()
        mock_client.query_endpoint.return_value = ([], 0, None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("data_go_mcp.open_assembly.server.AssemblyAPIClient", return_value=mock_client):
            result = await query_assembly(endpoint_code="nzmimeepazxkubdpn")

        assert result["count"] == 0
        assert result["has_more"] is False
        assert "파라미터" in result["message"]
