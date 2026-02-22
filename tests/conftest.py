"""テストフィクスチャ定義モジュール。"""

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_gdrive_credentials() -> Any:
    """モック化された OAuth2 認証情報フィクスチャ。

    Returns:
        モック化された認証情報オブジェクト
    """
    mock_creds = MagicMock()
    mock_creds.token = "mock_token"
    mock_creds.refresh_token = "mock_refresh_token"
    mock_creds.client_id = "mock_client_id"
    mock_creds.client_secret = "mock_client_secret"
    return mock_creds


@pytest.fixture
def mock_gdrive_service() -> Any:
    """モック化された Google Drive サービスフィクスチャ。

    Returns:
        モック化された Drive サービスオブジェクト
    """
    mock_service = MagicMock()
    mock_files = MagicMock()
    mock_service.files.return_value = mock_files
    return mock_service
