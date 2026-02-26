"""Google OAuth認証クライアントのテスト."""

from typing import Any
from unittest.mock import Mock

import pytest

from mizu_common.constants.google_scope import GoogleScope
from mizu_common.google_oauth_client import GoogleOAuthClient


def test_get_access_token_returns_refreshed_token(mocker: Any) -> None:
    """get_access_tokenがリフレッシュされたトークンを返すこと.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_access_token()を呼び出す。

    Assert:
        アクセストークンが返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_access_token"}
    mocker.patch("requests.post", return_value=mock_response)

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    # Act
    token = client.get_access_token()

    # Assert
    assert token == "new_access_token"


def test_get_access_token_raises_error_on_failure(mocker: Any) -> None:
    """トークン取得失敗時にRuntimeErrorが発生すること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_access_token()を呼び出す。

    Assert:
        RuntimeErrorが発生すること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "invalid_grant"
    mocker.patch("requests.post", return_value=mock_response)

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "invalid_refresh_token", scopes)

    # Act & Assert
    with pytest.raises(RuntimeError, match="アクセストークンの取得に失敗しました"):
        client.get_access_token()


def test_get_headers_returns_authorization_header(mocker: Any) -> None:
    """get_headersがAuthorizationヘッダーを返すこと.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_headers()を呼び出す。

    Assert:
        Authorizationヘッダーが正しく設定されていること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "test_access_token"}
    mocker.patch("requests.post", return_value=mock_response)

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    # Act
    headers = client.get_headers()

    # Assert
    assert headers == {"Authorization": "Bearer test_access_token"}


def test_get_access_token_caches_token(mocker: Any) -> None:
    """get_access_tokenがトークンをキャッシュすること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_access_token()を複数回呼び出す。

    Assert:
        2回目以降はAPIが呼ばれないこと。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "cached_token"}
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    # Act
    token1 = client.get_access_token()
    token2 = client.get_access_token()

    # Assert
    assert token1 == "cached_token"
    assert token2 == "cached_token"
    mock_post.assert_called_once()
