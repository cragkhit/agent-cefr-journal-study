import json
from unittest.mock import patch, mock_open

import pytest

from src.schemas.report import ReportStatus, ReportVisibility
from src.services.report_status import (
    _report_status, _lock, update_token_usage, save_status
)


class TestUpdateTokenUsage:
    """update_token_usage関数のテスト"""

    def setup_method(self):
        """各テスト前に_report_statusをクリアして初期化"""
        _report_status.clear()
        _report_status["test-slug"] = {
            "status": ReportStatus.READY.value,
            "title": "Test Report",
            "description": "Test Description",
            "visibility": ReportVisibility.PUBLIC.value,
            "is_pubcom": False,
            "created_at": "2023-01-01T00:00:00Z",
            "token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }

    def test_update_token_usage_all_values(self):
        """トークン使用量（合計、入力、出力）を正しく更新できることをテスト"""
        update_token_usage("test-slug", 100, 40, 60)

        assert _report_status["test-slug"]["token_usage"] == 100
        assert _report_status["test-slug"]["token_usage_input"] == 40
        assert _report_status["test-slug"]["token_usage_output"] == 60

    def test_update_token_usage_total_only(self):
        """合計トークン使用量のみを更新できることをテスト"""
        update_token_usage("test-slug", 300)

        assert _report_status["test-slug"]["token_usage"] == 300
        assert _report_status["test-slug"]["token_usage_input"] == 0
        assert _report_status["test-slug"]["token_usage_output"] == 0

    def test_update_token_usage_nonexistent_slug(self):
        """存在しないスラッグの場合は警告ログが出力されるだけで例外は発生しないことをテスト"""
        update_token_usage("non-existent-slug", 200, 80, 120)

        assert "test-slug" in _report_status
        assert "non-existent-slug" not in _report_status

    def test_update_token_usage_calls_save_status(self):
        """update_token_usage関数がsave_status関数を呼び出すことをテスト"""
        with patch("src.services.report_status.save_status") as mock_save_status:
            update_token_usage("test-slug", 400, 160, 240)

            mock_save_status.assert_called_once()

    def test_update_token_usage_with_none_values(self):
        """入力・出力トークン使用量にNoneを指定した場合のテスト"""
        _report_status["test-slug"]["token_usage_input"] = 50
        _report_status["test-slug"]["token_usage_output"] = 70

        update_token_usage("test-slug", 500, None, None)

        assert _report_status["test-slug"]["token_usage"] == 500
        assert _report_status["test-slug"]["token_usage_input"] == 50
        assert _report_status["test-slug"]["token_usage_output"] == 70
