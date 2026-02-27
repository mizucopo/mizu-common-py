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
    mocker.patch(
        "mizu_common.google_oauth_client.requests.post", return_value=mock_response
    )

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
    mocker.patch(
        "mizu_common.google_oauth_client.requests.post", return_value=mock_response
    )

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "invalid_refresh_token", scopes)

    # Act & Assert
    with pytest.raises(RuntimeError, match="アクセストークンの取得に失敗しました"):
        client.get_access_token()


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
    mock_post = mocker.patch(
        "mizu_common.google_oauth_client.requests.post", return_value=mock_response
    )

    scopes = [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    # Act
    token1 = client.get_access_token()
    token2 = client.get_access_token()

    # Assert
    assert token1 == "cached_token"
    assert token2 == "cached_token"
    mock_post.assert_called_once()


def test_device_authentication_completes_successfully_with_valid_credentials(
    mocker: Any,
) -> None:
    """有効な認証情報でデバイス認証が正常に完了すること.

    Arrange:
        有効なOAuthクライアントIDとシークレットを用意する。
        ユーザーが認証を承認するレスポンスをモックする。

    Act:
        GoogleOAuthClient.authenticate()を実行する。

    Assert:
        リフレッシュトークンが正常に取得されること。
        ユーザーに正しい認証指示が表示されること。
    """
    # Arrange
    client_id = "test_client_id"
    client_secret = "test_client_secret"
    scopes = [GoogleScope.DRIVE_FILE]

    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 5,
    }
    mock_post = mocker.Mock()
    mock_post.side_effect = [
        mocker.Mock(
            status_code=200,
            json=lambda: device_code_response,
            raise_for_status=lambda: None,
        ),
        mocker.Mock(
            status_code=200,
            json=lambda: {"refresh_token": "test_refresh_token"},
            raise_for_status=lambda: None,
        ),
    ]

    output_messages: list[str] = []

    def capture_output(msg: str) -> None:
        output_messages.append(msg)

    # Act
    result = GoogleOAuthClient.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        output_handler=capture_output,
        http_post=mock_post,
    )

    # Assert
    assert result == "test_refresh_token"
    assert "https://www.google.com/device" in output_messages[0]
    assert "ABCD-1234" in output_messages[1]


@pytest.mark.parametrize(
    "error_response",
    [
        {"error": "access_denied"},
        {"error": "expired_token"},
    ],
    ids=["ユーザー拒否", "有効期限切れ"],
)
def test_device_authentication_returns_none_on_oauth_errors(
    mocker: Any, error_response: dict[str, str]
) -> None:
    """OAuthエラーが発生した場合、デバイス認証がNoneを返すこと.

    Arrange:
        有効なOAuthクライアント認証情報を用意する。
        OAuthエラーレスポンスをモックする。

    Act:
        GoogleOAuthClient.authenticate()を実行する。

    Assert:
        Noneが返されること。
    """
    # Arrange
    client_id = "test_client_id"
    client_secret = "test_client_secret"
    scopes = [GoogleScope.DRIVE_FILE]

    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 1,
    }

    mock_post = mocker.Mock()
    mock_post.side_effect = [
        mocker.Mock(
            status_code=200,
            json=lambda: device_code_response,
            raise_for_status=lambda: None,
        ),
        mocker.Mock(
            status_code=400,
            json=lambda: error_response,
            raise_for_status=lambda: None,
        ),
    ]

    # Act
    result = GoogleOAuthClient.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result is None


def test_device_authentication_succeeds_after_slow_down_response(
    mocker: Any,
) -> None:
    """Googleからslow_down応答が返された場合でも、最終的に認証が成功すること.

    Arrange:
        有効なOAuthクライアント認証情報を用意する。
        Googleがslow_down応答を返すようモックする。

    Act:
        GoogleOAuthClient.authenticate()を実行する。

    Assert:
        最終的にリフレッシュトークンが取得されること。
    """
    # Arrange
    mocker.patch("time.sleep")  # 実際のsleepを回避

    client_id = "test_client_id"
    client_secret = "test_client_secret"
    scopes = [GoogleScope.DRIVE_FILE]

    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 2,
    }

    mock_post = mocker.Mock()
    mock_post.side_effect = [
        mocker.Mock(
            status_code=200,
            json=lambda: device_code_response,
            raise_for_status=lambda: None,
        ),
        mocker.Mock(
            status_code=400,
            json=lambda: {"error": "slow_down"},
            raise_for_status=lambda: None,
        ),
        mocker.Mock(
            status_code=200,
            json=lambda: {"refresh_token": "test_refresh_token"},
            raise_for_status=lambda: None,
        ),
    ]

    # Act
    result = GoogleOAuthClient.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result == "test_refresh_token"
