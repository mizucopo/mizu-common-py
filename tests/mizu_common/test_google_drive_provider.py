"""GoogleDriveProvider のアップロード機能のテスト。"""

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
