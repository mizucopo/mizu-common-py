"""Tests for GoogleDriveProvider upload and authentication functionality."""

import os
from typing import Any

import pytest

from mizu_common.google_drive_provider import GoogleDriveProvider


def test_upload_creates_new_file_when_not_exists(
    mock_gdrive_credentials: Any, mock_gdrive_service: Any
) -> None:
    """同名ファイルが存在しない場合、新規ファイルが作成されること.

    Given:
        - 有効な認証情報
        - 同名ファイルが存在しない

    When:
        - GoogleDriveProvider.upload() を実行

    Then:
        - files().create() が呼ばれる
        - files().update() は呼ばれない
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # 検索: 同名ファイルなし
    mock_list_req.execute.return_value = {"files": []}

    # チャンクアップロードのモック
    mock_create_req.next_chunk.return_value = (None, {"id": "new_file_id"})

    test_file = "/tmp/test_new_file.txt"
    with open(test_file, "w") as f:
        f.write("new content")

    provider = GoogleDriveProvider(
        folder_id="test_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "new_file.txt")

    # Assert
    mock_files.list.assert_called_once()
    mock_files.create.assert_called_once()
    mock_files.update.assert_not_called()

    # Cleanup
    os.remove(test_file)


def test_upload_updates_existing_file_when_exists(
    mock_gdrive_credentials: Any, mock_gdrive_service: Any
) -> None:
    """同名ファイルが存在する場合、既存ファイルが更新されること.

    Given:
        - 有効な認証情報
        - 同名ファイルが存在する

    When:
        - GoogleDriveProvider.upload() を実行

    Then:
        - files().update() が呼ばれる
        - files().create() は呼ばれない
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_update_req = mock_files.update.return_value

    # 検索: 同名ファイルが存在
    mock_list_req.execute.return_value = {
        "files": [{"id": "existing_file_id", "name": "existing.txt"}]
    }

    # チャンクアップロードのモック
    mock_update_req.next_chunk.return_value = (None, {"id": "existing_file_id"})

    test_file = "/tmp/test_existing_file.txt"
    with open(test_file, "w") as f:
        f.write("updated content")

    provider = GoogleDriveProvider(
        folder_id="test_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "existing.txt")

    # Assert
    mock_files.list.assert_called_once()
    mock_files.update.assert_called_once()
    mock_files.create.assert_not_called()

    # Cleanup
    os.remove(test_file)


def test_file_upload_raises_error_when_google_drive_api_fails(
    mock_gdrive_credentials: Any, mock_gdrive_service: Any
) -> None:
    """Google Drive API が失敗した場合、適切な例外が発生すること.

    Given:
        - 有効な認証情報
        - Google Drive API がエラーを返す

    When:
        - GoogleDriveProvider.upload() を実行

    Then:
        - RuntimeError が発生する
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # 検索: 同名ファイルなし
    mock_list_req.execute.return_value = {"files": []}

    # API エラーをシミュレート
    mock_create_req.next_chunk.side_effect = RuntimeError("API Error: 403 Forbidden")

    test_file = "/tmp/test_backup.txt"
    with open(test_file, "w") as f:
        f.write("test content")

    provider = GoogleDriveProvider(
        folder_id="test_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act & Assert
    # RuntimeError が発生すること
    with pytest.raises(RuntimeError):
        provider.upload(test_file, "backup.txt")

    # Cleanup
    os.remove(test_file)


def test_device_authentication_completes_successfully_with_valid_credentials(
    mocker: Any,
) -> None:
    """有効な認証情報でデバイス認証が正常に完了すること.

    Given:
        - 有効な OAuth クライアント ID とシークレット
        - ユーザーが認証を承認する

    When:
        - GoogleDriveProvider.authenticate() を実行

    Then:
        - refresh token が正常に取得できる
        - ユーザーに正しい認証指示が表示される
    """
    # Arrange
    client_id = "test_client_id"
    client_secret = "test_client_secret"

    # デバイスコード取得のモック
    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 5,
    }
    mock_post = mocker.Mock()

    # 1回目: デバイスコード取得
    # 2回目: トークン取得成功
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

    output_messages = []

    def capture_output(msg: str) -> None:
        output_messages.append(msg)

    # Act
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        output_handler=capture_output,
        http_post=mock_post,
    )

    # Assert
    assert result == "test_refresh_token"

    # ユーザーに正しい指示が表示されたこと
    assert len(output_messages) == 3
    assert "https://www.google.com/device" in output_messages[0]
    assert "ABCD-1234" in output_messages[1]


@pytest.mark.parametrize(
    "error_response",
    [
        {"error": "access_denied"},  # ユーザー拒否
        {"error": "expired_token"},  # 有効期限切れ
    ],
)
def test_device_authentication_returns_none_on_oauth_errors(
    mocker: Any, error_response: dict[str, str]
) -> None:
    """OAuthエラーが発生した場合、デバイス認証が None を返すこと.

    Given:
        - 有効な OAuth クライアント認証情報
        - OAuthエラー（ユーザー拒否または有効期限切れ）が発生する

    When:
        - GoogleDriveProvider.authenticate() を実行

    Then:
        - None が返される
    """
    # Arrange
    client_id = "test_client_id"
    client_secret = "test_client_secret"

    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 1,  # 短くしてテストを高速化
    }

    mock_post = mocker.Mock()
    mock_post.side_effect = [
        # デバイスコード取得
        mocker.Mock(
            status_code=200,
            json=lambda: device_code_response,
            raise_for_status=lambda: None,
        ),
        # OAuthエラー
        mocker.Mock(
            status_code=400,
            json=lambda: error_response,
            raise_for_status=lambda: None,
        ),
    ]

    # Act
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result is None


def test_device_authentication_increases_polling_interval_on_slow_down_request(
    mocker: Any,
) -> None:
    """Google からポーリング間隔の増加を要求された場合、認証が成功すること.

    Given:
        - 有効な OAuth クライアント認証情報
        - Google がポーリング間隔の増加を要求する

    When:
        - GoogleDriveProvider.authenticate() を実行

    Then:
        - 最終的に認証が成功する
    """
    # Arrange
    # time.sleep をモック化してテストを高速化
    mock_sleep = mocker.patch("time.sleep")

    client_id = "test_client_id"
    client_secret = "test_client_secret"

    device_code_response = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 2,
    }

    mock_post = mocker.Mock()
    mock_post.side_effect = [
        # デバイスコード取得
        mocker.Mock(
            status_code=200,
            json=lambda: device_code_response,
            raise_for_status=lambda: None,
        ),
        # slow down 要求
        mocker.Mock(
            status_code=400,
            json=lambda: {"error": "slow_down"},
            raise_for_status=lambda: None,
        ),
        # 認証成功
        mocker.Mock(
            status_code=200,
            json=lambda: {"refresh_token": "test_refresh_token"},
            raise_for_status=lambda: None,
        ),
    ]

    # Act
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result == "test_refresh_token"
    # slow_downでintervalが2→7に増加した後、sleep(7)が1回呼ばれる
    mock_sleep.assert_called_once_with(7)


def test_provider_initialization_succeeds_when_credentials_are_provided(
    mocker: Any,
) -> None:
    """認証情報が正しい場合、プロバイダが正常に作成されること.

    Given:
        - すべての認証情報が提供されている

    When:
        - GoogleDriveProvider.from_credentials() を実行

    Then:
        - GoogleDriveProvider インスタンスが正常に作成される
        - インスタンスに正しい folder_id が設定される
    """
    # Arrange
    # Google API ビルドをモック
    mocker.patch("mizu_common.google_drive_provider.build")

    # Act
    provider = GoogleDriveProvider.from_credentials(
        folder_id="test_folder_id",
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
    )

    # Assert
    assert provider.folder_id == "test_folder_id"
    assert provider.creds.refresh_token == "test_refresh_token"
    assert provider.creds.client_id == "test_client_id"
    assert provider.creds.client_secret == "test_client_secret"
