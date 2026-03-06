"""Unit tests for AssemblyAPIClient."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from data_go_mcp.open_assembly.client import AssemblyAPIClient


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("ASSEMBLY_API_KEY", "test-api-key-1234")


@pytest.fixture
def sample_bill_response():
    return {
        "nzmimeepazxkubdpn": [
            {
                "head": [
                    {"list_total_count": 47},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {
                "row": [
                    {
                        "BILL_ID": "PRC_A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5",
                        "BILL_NO": "2200001",
                        "BILL_NAME": "테스트법률안",
                        "RST_PROPOSER": "홍길동",
                        "PUBL_PROPOSER": "홍길동, 김철수, 이영희",
                        "PROPOSE_DT": "20240101",
                        "PROC_RESULT": None,
                        "AGE": "22",
                    }
                ]
            },
        ]
    }


@pytest.fixture
def sample_empty_response():
    return {
        "nzmimeepazxkubdpn": [
            {
                "head": [
                    {"list_total_count": 0},
                    {"RESULT": {"CODE": "INFO-200", "MESSAGE": "검색된 데이터가 없습니다."}},
                ]
            }
        ]
    }


class TestParseResponse:
    def test_normal_response(self, mock_env, sample_bill_response):
        client = AssemblyAPIClient.__new__(AssemblyAPIClient)
        client.api_key = "test"
        rows, total = client._parse_response(sample_bill_response, "nzmimeepazxkubdpn")
        assert len(rows) == 1
        assert rows[0]["BILL_NO"] == "2200001"
        assert total == 47

    def test_empty_response_info200(self, mock_env, sample_empty_response):
        client = AssemblyAPIClient.__new__(AssemblyAPIClient)
        client.api_key = "test"
        rows, total = client._parse_response(sample_empty_response, "nzmimeepazxkubdpn")
        assert rows == []
        assert total == 0

    def test_error_response_raises(self, mock_env):
        client = AssemblyAPIClient.__new__(AssemblyAPIClient)
        client.api_key = "test"
        error_response = {
            "nzmimeepazxkubdpn": [
                {
                    "head": [
                        {"list_total_count": 0},
                        {"RESULT": {"CODE": "ERROR-290", "MESSAGE": "인증키가 유효하지 않습니다."}},
                    ]
                }
            ]
        }
        with pytest.raises(ValueError, match="ERROR-290"):
            client._parse_response(error_response, "nzmimeepazxkubdpn")

    def test_single_row_dict_normalized_to_list(self, mock_env):
        """단건 응답(dict)이 list로 정규화되는지 확인."""
        client = AssemblyAPIClient.__new__(AssemblyAPIClient)
        client.api_key = "test"
        single_row_response = {
            "ALLBILL": [
                {
                    "head": [
                        {"list_total_count": 1},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {"row": {"BILL_NO": "2200001", "BILL_NM": "단건법률안"}},
            ]
        }
        rows, total = client._parse_response(single_row_response, "ALLBILL")
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert rows[0]["BILL_NO"] == "2200001"
        assert total == 1

    def test_total_count_extracted_correctly(self, mock_env, sample_bill_response):
        """list_total_count가 total에 올바르게 반영되는지 확인."""
        client = AssemblyAPIClient.__new__(AssemblyAPIClient)
        client.api_key = "test"
        _, total = client._parse_response(sample_bill_response, "nzmimeepazxkubdpn")
        assert total == 47


class TestMissingApiKey:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ASSEMBLY_API_KEY"):
            AssemblyAPIClient()


class TestSearchBills:
    @pytest.mark.asyncio
    async def test_search_bills_calls_correct_endpoint(self, mock_env, sample_bill_response):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = sample_bill_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.search_bills(age="22")

            assert len(rows) == 1
            assert total == 47
            call_url = mock_get.call_args[0][0]
            assert "nzmimeepazxkubdpn" in call_url

    @pytest.mark.asyncio
    async def test_search_bills_empty_result(self, mock_env, sample_empty_response):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = sample_empty_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.search_bills(age="22", bill_name="존재하지않는법안")

            assert rows == []
            assert total == 0

    @pytest.mark.asyncio
    async def test_search_bills_date_filter_client_side(self, mock_env):
        """날짜 필터가 client-side에서 PROPOSE_DT 기준으로 동작하는지 확인."""
        bulk_response = {
            "nzmimeepazxkubdpn": [
                {
                    "head": [
                        {"list_total_count": 3},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {"BILL_NO": "2200001", "PROPOSE_DT": "20231215", "BILL_NAME": "before"},
                        {"BILL_NO": "2200002", "PROPOSE_DT": "20240315", "BILL_NAME": "in-range"},
                        {"BILL_NO": "2200003", "PROPOSE_DT": "20250101", "BILL_NAME": "after"},
                    ]
                },
            ]
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = bulk_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.search_bills(
                    age="22",
                    propose_dt_from="20240101",
                    propose_dt_to="20241231",
                )

            assert total == 1
            assert len(rows) == 1
            assert rows[0]["BILL_NO"] == "2200002"


class TestGetMemberVotes:
    @pytest.mark.asyncio
    async def test_member_votes_calls_correct_endpoint(self, mock_env):
        vote_response = {
            "nojepdqqaweusdfbi": [
                {
                    "head": [
                        {"list_total_count": 295},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {
                            "HG_NM": "홍길동",
                            "POLY_NM": "더불어민주당",
                            "ORIG_NM": "서울 강남갑",
                            "RESULT_VOTE_MOD": "찬성",
                            "BILL_NO": "2216983",
                            "AGE": "22",
                        }
                    ]
                },
            ]
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = vote_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_member_votes(
                    bill_id="PRC_T2M6W0F2I1W2T1X7T4K2Q5A9J4P2M5",
                    age="22",
                )

        assert len(rows) == 1
        assert total == 295
        assert rows[0]["RESULT_VOTE_MOD"] == "찬성"
        call_url = mock_get.call_args[0][0]
        assert "nojepdqqaweusdfbi" in call_url

    @pytest.mark.asyncio
    async def test_member_votes_passes_age_and_bill_id(self, mock_env):
        """AGE와 BILL_ID 모두 요청 파라미터에 포함되는지 확인."""
        vote_response = {
            "nojepdqqaweusdfbi": [
                {
                    "head": [
                        {"list_total_count": 0},
                        {"RESULT": {"CODE": "INFO-200", "MESSAGE": "검색된 데이터가 없습니다."}},
                    ]
                }
            ]
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = vote_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_member_votes(
                    bill_id="PRC_TEST123",
                    age="22",
                    vote_result="찬성",
                )

        call_params = mock_get.call_args[1]["params"]
        assert call_params["BILL_ID"] == "PRC_TEST123"
        assert call_params["AGE"] == "22"
        assert call_params["RESULT_VOTE_MOD"] == "찬성"
        assert rows == []
        assert total == 0


def _make_api_response(endpoint: str, rows: list, total: int) -> dict:
    """Build a minimal valid API response fixture for a given endpoint."""
    return {
        endpoint: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": rows},
        ]
    }


def _make_empty_response(endpoint: str) -> dict:
    return {
        endpoint: [
            {
                "head": [
                    {"list_total_count": 0},
                    {"RESULT": {"CODE": "INFO-200", "MESSAGE": "검색된 데이터가 없습니다."}},
                ]
            }
        ]
    }


class TestGetPendingBills:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, mock_env):
        response = _make_api_response(
            "nwbqublzajtcqpdae",
            [{"BILL_NO": "2217500", "BILL_NAME": "계류법안"}],
            total=8900,
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_pending_bills(age="22")

        assert len(rows) == 1
        assert total == 8900
        assert "nwbqublzajtcqpdae" in mock_get.call_args[0][0]

    @pytest.mark.asyncio
    async def test_passes_age_and_filters(self, mock_env):
        response = _make_empty_response("nwbqublzajtcqpdae")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                await client.get_pending_bills(
                    age="22", committee="법제사법위원회", proposer="홍길동"
                )

        params = mock_get.call_args[1]["params"]
        assert params["AGE"] == "22"
        assert params["COMMITTEE"] == "법제사법위원회"
        assert params["PROPOSER"] == "홍길동"


class TestGetPlenaryAgenda:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, mock_env):
        response = _make_api_response(
            "nayjnliqaexiioauy",
            [{"BILL_NO": "2217501", "BILL_NAME": "부의법안", "SESS_NO": "1"}],
            total=3,
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_plenary_agenda(age="22")

        assert len(rows) == 1
        assert total == 3
        assert "nayjnliqaexiioauy" in mock_get.call_args[0][0]

    @pytest.mark.asyncio
    async def test_session_filter_passed(self, mock_env):
        response = _make_empty_response("nayjnliqaexiioauy")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                await client.get_plenary_agenda(age="22", session="2")

        params = mock_get.call_args[1]["params"]
        assert params["AGE"] == "22"
        assert params["SESS_NO"] == "2"


class TestGetBillCommitteeReview:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, mock_env):
        response = _make_api_response(
            "BILLJUDGECONF",
            [{"BILL_ID": "PRC_TEST123", "CMIT_NM": "법제사법위원회", "MTG_DT": "20240315"}],
            total=2,
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_bill_committee_review(bill_id="PRC_TEST123")

        assert len(rows) == 1
        assert total == 2
        assert rows[0]["CMIT_NM"] == "법제사법위원회"
        assert "BILLJUDGECONF" in mock_get.call_args[0][0]

    @pytest.mark.asyncio
    async def test_passes_bill_id(self, mock_env):
        response = _make_empty_response("BILLJUDGECONF")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                await client.get_bill_committee_review(bill_id="PRC_ABCDEF")

        params = mock_get.call_args[1]["params"]
        assert params["BILL_ID"] == "PRC_ABCDEF"


class TestTimeoutHandling:
    @pytest.mark.asyncio
    async def test_timeout_raises_descriptive_error(self, mock_env):
        """TimeoutException이 명확한 에러 메시지와 함께 ValueError로 변환되는지 확인."""
        import httpx
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")

            async with AssemblyAPIClient() as client:
                with pytest.raises(ValueError, match="timed out"):
                    await client.search_bills(age="22")


class TestGetMemberInfo:
    @pytest.mark.asyncio
    async def test_get_member_info_calls_correct_endpoint(self, mock_env):
        member_response = {
            "ALLNAMEMBER": [
                {
                    "head": [
                        {"list_total_count": 1},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {
                            "NAAS_NM": "홍길동",
                            "NAAS_CD": "A1B2C3D4",
                            "NAAS_CH_NM": "洪吉東",
                            "NAAS_EN_NM": "HONG Gildong",
                            "NTR_DIV": "남",
                            "BIRDY_DT": "19700101",
                            "GTELT_ERACO": "제22대",
                            "PLPT_NM": "더불어민주당",
                            "ELECD_NM": "서울 강남갑",
                            "ELECD_DIV_NM": "지역구",
                            "BLNG_CMIT_NM": "법제사법위원회",
                            "RLCT_DIV_NM": "초선",
                        }
                    ]
                },
            ]
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = member_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                rows, total = await client.get_member_info(unit_cd="100022", name="홍길동")

            assert len(rows) == 1
            assert total == 1
            assert rows[0]["HG_NM"] == "홍길동"
            call_url = mock_get.call_args[0][0]
            assert "ALLNAMEMBER" in call_url
