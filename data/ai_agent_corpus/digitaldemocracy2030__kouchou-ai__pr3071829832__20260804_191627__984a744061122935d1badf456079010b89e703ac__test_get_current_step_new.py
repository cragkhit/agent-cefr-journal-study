import json
from unittest.mock import patch, mock_open

import pytest

from src.routers.admin_report import get_current_step


@pytest.mark.asyncio
async def test_get_current_step_with_token_usage(async_client, test_slug):
    """get_current_stepエンドポイントがトークン使用量情報を返すことをテスト"""
    status_data = {
        "status": "in_progress",
        "current_job": "extraction",
        "total_token_usage": 1500,
        "token_usage_input": 1000,
        "token_usage_output": 500
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "extraction"
            assert data["token_usage"] == 1500
            assert data["token_usage_input"] == 1000
            assert data["token_usage_output"] == 500


@pytest.mark.asyncio
async def test_get_current_step_with_no_token_usage(async_client, test_slug):
    """get_current_stepエンドポイントがトークン使用量情報がない場合でも適切に動作することをテスト"""
    status_data = {
        "status": "in_progress",
        "current_job": "extraction"
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "extraction"
            assert data["token_usage"] == 0
            assert data["token_usage_input"] == 0
            assert data["token_usage_output"] == 0


@pytest.mark.asyncio
async def test_get_current_step_with_error(async_client, test_slug):
    """get_current_stepエンドポイントがエラー時に適切なレスポンスを返すことをテスト"""
    status_data = {
        "status": "error",
        "error": "Test error",
        "total_token_usage": 100,
        "token_usage_input": 70,
        "token_usage_output": 30
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "error"
            assert data["token_usage"] == 100
            assert data["token_usage_input"] == 70
            assert data["token_usage_output"] == 30


@pytest.mark.asyncio
async def test_get_current_step_file_not_found(async_client, test_slug):
    """get_current_stepエンドポイントがファイルが存在しない場合に適切なレスポンスを返すことをテスト"""
    with patch("os.path.exists", return_value=False):
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == "error"
        assert data["token_usage"] == 0
        assert data["token_usage_input"] == 0
        assert data["token_usage_output"] == 0


@pytest.mark.asyncio
async def test_get_current_step_exception(async_client, test_slug):
    """get_current_stepエンドポイントが例外発生時に適切なレスポンスを返すことをテスト"""
    with patch("os.path.exists", side_effect=Exception("Test exception")):
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == "error"
        assert data["token_usage"] == 0
        assert data["token_usage_input"] == 0
        assert data["token_usage_output"] == 0
