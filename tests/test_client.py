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
    async def test_search_bills_date_params_passed(self, mock_env, sample_bill_response):
        """발의일 날짜 필터 파라미터(STR_DT, END_DT)가 요청에 포함되는지 확인."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = sample_bill_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            async with AssemblyAPIClient() as client:
                await client.search_bills(
                    age="22",
                    propose_dt_from="20240101",
                    propose_dt_to="20241231",
                )

            call_kwargs = mock_get.call_args[1]["params"]
            assert call_kwargs["STR_DT"] == "20240101"
            assert call_kwargs["END_DT"] == "20241231"


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


class TestGetMemberInfo:
    @pytest.mark.asyncio
    async def test_get_member_info_calls_correct_endpoint(self, mock_env):
        member_response = {
            "nwvrqwxyaytdsfvhu": [
                {
                    "head": [
                        {"list_total_count": 1},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {
                            "HG_NM": "홍길동",
                            "POLY_NM": "더불어민주당",
                            "ORIG_NM": "서울 강남갑",
                            "CMIT_NM": "법제사법위원회",
                            "MONA_CD": "A1B2C3D4",
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
            assert "nwvrqwxyaytdsfvhu" in call_url
