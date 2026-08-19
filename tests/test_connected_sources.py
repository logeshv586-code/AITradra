import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.connected_source_adapter import ConnectedSourceAdapter, connected_sources


@pytest.mark.asyncio
async def test_polygon_price_success():
    adapter = ConnectedSourceAdapter()
    connection = {
        "id": "conn_poly_1",
        "name": "My Polygon Source",
        "category": "market_data",
        "provider": "polygon",
        "secrets": {"api_key": "test_polygon_key_123"},
        "config": {},
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "ticker": "AAPL",
        "queryCount": 1,
        "resultsCount": 1,
        "adjusted": True,
        "results": [
            {
                "v": 50000000,
                "vw": 182.5,
                "o": 180.0,
                "c": 185.0,
                "h": 186.0,
                "l": 179.5,
                "t": 1700000000000,
                "n": 400000,
            }
        ],
        "status": "OK",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        res = await adapter._price_from_connection(connection, "AAPL")

        assert res is not None
        assert res["px"] == 185.0
        assert res["open"] == 180.0
        assert res["high"] == 186.0
        assert res["low"] == 179.5
        assert res["volume"] == 50000000
        assert res["chg"] == 5.0
        assert res["pct_chg"] == pytest.approx(2.7777777777777777)
        assert res["provider"] == "polygon"
        assert res["timestamp"] == 1700000000000

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.polygon.io/v2/aggs/ticker/AAPL/prev" in args[0]
        assert kwargs["params"] == {"adjusted": "true", "apiKey": "test_polygon_key_123"}


@pytest.mark.asyncio
async def test_polygon_missing_api_key():
    adapter = ConnectedSourceAdapter()
    connection = {
        "id": "conn_poly_nokey",
        "name": "Polygon No Key",
        "category": "market_data",
        "provider": "polygon",
        "secrets": {"api_key": ""},
        "config": {},
    }

    res = await adapter._price_from_connection(connection, "AAPL")
    assert res is None


@pytest.mark.asyncio
async def test_polygon_empty_results():
    adapter = ConnectedSourceAdapter()
    connection = {
        "id": "conn_poly_empty",
        "name": "Polygon Empty",
        "category": "market_data",
        "provider": "polygon",
        "secrets": {"api_key": "valid_key"},
        "config": {},
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "OK", "results": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        res = await adapter._price_from_connection(connection, "AAPL")
        assert res is None


@pytest.mark.asyncio
async def test_polygon_http_error():
    adapter = ConnectedSourceAdapter()
    connection = {
        "id": "conn_poly_error",
        "name": "Polygon Error",
        "category": "market_data",
        "provider": "polygon",
        "secrets": {"api_key": "bad_key"},
        "config": {},
    }

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with pytest.raises(httpx.HTTPStatusError):
            await adapter._price_from_connection(connection, "AAPL")
