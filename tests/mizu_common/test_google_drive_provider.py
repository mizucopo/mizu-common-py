"""GoogleDriveProvider のアップロード機能と認証機能のテスト。"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from mizu_common.google_drive_provider import GoogleDriveProvider


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


@pytest.fixture
def test_file(tmp_path: Any) -> str:
    """テスト用の一時ファイルを作成するフィクスチャ。

    Returns:
        テスト用ファイルのパス
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return str(file_path)


@pytest.mark.parametrize(
    "existing_files,expected_method",
    [
        ([], "create"),  # 新規作成
        ([{"id": "existing_id", "name": "test.txt"}], "update"),  # 既存更新
    ],
    ids=["新規作成", "既存更新"],
)
def test_upload_delegates_to_correct_api_method(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
    test_file: str,
    existing_files: list[dict[str, str]],
    expected_method: str,
) -> None:
    """同名ファイルの有無に応じて適切な API メソッドが呼ばれること。

    Given:
        - 有効な認証情報

    When:
        - GoogleDriveProvider.upload() を実行

    Then:
        - ファイルが存在しない場合: files().create() が呼ばれる
        - ファイルが存在する場合: files().update() が呼ばれる
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value
    mock_update_req = mock_files.update.return_value

    mock_list_req.execute.return_value = {"files": existing_files}
    mock_create_req.next_chunk.return_value = (None, {"id": "file_id"})
    mock_update_req.next_chunk.return_value = (None, {"id": "file_id"})

    provider = GoogleDriveProvider(
        folder_id="test_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "test.txt")

    # Assert
    mock_files.list.assert_called_once()
    if expected_method == "create":
        mock_files.create.assert_called_once()
        mock_files.update.assert_not_called()
    else:
        mock_files.update.assert_called_once()
        mock_files.create.assert_not_called()


def test_device_authentication_completes_successfully_with_valid_credentials(
    mocker: Any,
) -> None:
    """有効な認証情報でデバイス認証が正常に完了すること。

    Given:
        - 有効な OAuth クライアント ID とシークレット
        - ユーザーが認証を承認する

    When:
        - GoogleDriveProvider.authenticate() を実行

    Then:
        - リフレッシュトークンが正常に取得できる
        - ユーザーに正しい認証指示が表示される
    """
    # Arrange
    client_id = "test_client_id"
    client_secret = "test_client_secret"

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
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
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
    """OAuth エラーが発生した場合、デバイス認証が None を返すこと。

    Given:
        - 有効な OAuth クライアント認証情報
        - OAuth エラーが発生する

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
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result is None


def test_device_authentication_increases_polling_interval_on_slow_down(
    mocker: Any,
) -> None:
    """Google からポーリング間隔の増加を要求された場合、認証が成功すること。

    Given:
        - 有効な OAuth クライアント認証情報
        - Google がポーリング間隔の増加を要求する

    When:
        - GoogleDriveProvider.authenticate() を実行

    Then:
        - ポーリング間隔が増加する
        - 最終的に認証が成功する
    """
    # Arrange
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
    result = GoogleDriveProvider.authenticate(
        client_id=client_id,
        client_secret=client_secret,
        output_handler=lambda _: None,
        http_post=mock_post,
    )

    # Assert
    assert result == "test_refresh_token"
    # slow_down で interval が 2 → 7 に増加した後、sleep(7) が呼ばれる
    mock_sleep.assert_called_once_with(7)
