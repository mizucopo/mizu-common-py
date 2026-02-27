"""Google OAuth認証クライアントのテスト."""

from typing import Any
from unittest.mock import Mock

import pytest
import requests

from mizu_common.constants.google_scope import GoogleScope
from mizu_common.google_oauth_client import GoogleOAuthClient


def test_get_access_token_caches_token(mocker: Any) -> None:
    """get_access_tokenがトークンをキャッシュすること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_access_token()を複数回呼び出す。

    Assert:
        トークンが返されること。
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


def test_get_access_token_force_refresh(mocker: Any) -> None:
    """force_refresh=Trueで強制的にトークンが更新されること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。
        すでにキャッシュされたトークンがある状態にする。

    Act:
        get_access_token(force_refresh=True)を呼び出す。

    Assert:
        トークンが強制的に更新されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_token"}
    mock_post = mocker.patch(
        "mizu_common.google_oauth_client.requests.post", return_value=mock_response
    )

    scopes = [GoogleScope.YOUTUBE_READONLY]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)
    # 最初のトークン取得
    client.get_access_token()

    # Act
    token = client.get_access_token(force_refresh=True)

    # Assert
    assert token == "new_token"
    assert mock_post.call_count == 2


@pytest.mark.parametrize(
    "first_call_result,expected_refresh_count,expected_call_count",
    [
        ("success", 0, 1),
        ("401_then_success", 1, 2),
    ],
    ids=["初回成功", "401エラー後リトライ成功"],
)
def test_refresh_on_unauthorized(
    mocker: Any,
    first_call_result: str,
    expected_refresh_count: int,
    expected_call_count: int,
) -> None:
    """refresh_on_unauthorizedの正常系を検証すること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。
        シナリオに応じたAPI呼び出しを用意する。

    Act:
        refresh_on_unauthorized()を実行する。

    Assert:
        期待される結果が返されること。
        トークンリフレッシュ回数が期待通りであること。
    """
    # Arrange
    mock_refresh_response = Mock()
    mock_refresh_response.status_code = 200
    mock_refresh_response.json.return_value = {"access_token": "new_token"}
    mock_post = mocker.patch(
        "mizu_common.google_oauth_client.requests.post",
        return_value=mock_refresh_response,
    )

    scopes = [GoogleScope.YOUTUBE_READONLY]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    call_count = 0

    def api_call() -> str:
        nonlocal call_count
        call_count += 1
        if first_call_result == "401_then_success" and call_count == 1:
            mock_error_response = Mock()
            mock_error_response.status_code = 401
            error = requests.exceptions.HTTPError()
            error.response = mock_error_response
            raise error
        return "success"

    # Act
    result = client.refresh_on_unauthorized(api_call)

    # Assert
    assert result == "success"
    assert call_count == expected_call_count
    assert mock_post.call_count == expected_refresh_count


def test_refresh_on_unauthorized_raises_on_non_401(mocker: Any) -> None:
    """401以外のエラーはそのままraiseされること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。
        500エラーを発生させるAPI呼び出しを用意する。

    Act:
        refresh_on_unauthorized()を実行する。

    Assert:
        例外がそのままraiseされること。
        トークンリフレッシュが呼ばれないこと。
    """
    # Arrange
    mock_post = mocker.patch("mizu_common.google_oauth_client.requests.post")

    scopes = [GoogleScope.YOUTUBE_READONLY]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    def api_call() -> str:
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        error = requests.exceptions.HTTPError()
        error.response = mock_error_response
        raise error

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError):
        client.refresh_on_unauthorized(api_call)

    mock_post.assert_not_called()


def test_refresh_on_unauthorized_raises_on_second_failure(mocker: Any) -> None:
    """リフレッシュ後も失敗したら例外が投げられること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。
        常に401エラーを発生させるAPI呼び出しを用意する。

    Act:
        refresh_on_unauthorized()を実行する。

    Assert:
        2回目の401エラーがraiseされること。
    """
    # Arrange
    mock_refresh_response = Mock()
    mock_refresh_response.status_code = 200
    mock_refresh_response.json.return_value = {"access_token": "new_token"}
    mock_post = mocker.patch(
        "mizu_common.google_oauth_client.requests.post",
        return_value=mock_refresh_response,
    )

    scopes = [GoogleScope.YOUTUBE_READONLY]
    client = GoogleOAuthClient("client_id", "refresh_token", scopes)

    call_count = 0

    def api_call() -> str:
        nonlocal call_count
        call_count += 1
        # 常に401エラーを発生させる
        mock_error_response = Mock()
        mock_error_response.status_code = 401
        error = requests.exceptions.HTTPError()
        error.response = mock_error_response
        raise error

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError):
        client.refresh_on_unauthorized(api_call)

    assert call_count == 2
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

    mock_post = mocker.patch("mizu_common.google_oauth_client.requests.post")
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

    mock_post = mocker.patch("mizu_common.google_oauth_client.requests.post")
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

    mock_post = mocker.patch("mizu_common.google_oauth_client.requests.post")
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
    )

    # Assert
    assert result == "test_refresh_token"
