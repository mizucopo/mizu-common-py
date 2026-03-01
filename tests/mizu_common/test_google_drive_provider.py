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


# ============================================================
# _find_folder テスト
# ============================================================


def test_find_folder_returns_id_when_exists(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """フォルダが存在する場合にIDが返されること。

    Given:
        - 指定した名前のフォルダが親フォルダ内に存在する

    When:
        - _find_folder() を実行

    Then:
        - フォルダIDが返されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_list_req.execute.return_value = {"files": [{"id": "folder_id_123"}]}

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._find_folder("subfolder", "root_folder")

    # Assert
    assert result == "folder_id_123"


def test_find_folder_returns_none_when_not_exists(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """フォルダが存在しない場合にNoneが返されること。

    Given:
        - 指定した名前のフォルダが親フォルダ内に存在しない

    When:
        - _find_folder() を実行

    Then:
        - Noneが返されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_list_req.execute.return_value = {"files": []}

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._find_folder("nonexistent", "root_folder")

    # Assert
    assert result is None


# ============================================================
# _create_folder テスト
# ============================================================


def test_create_folder_returns_new_id(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """フォルダ作成時に新しいIDが返されること。

    Given:
        - 親フォルダが存在する

    When:
        - _create_folder() を実行

    Then:
        - files().create() が呼ばれ、新しいフォルダIDが返されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_create_req = mock_files.create.return_value
    mock_create_req.execute.return_value = {"id": "new_folder_id"}

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._create_folder("new_folder", "root_folder")

    # Assert
    assert result == "new_folder_id"
    mock_files.create.assert_called_once()
    call_args = mock_files.create.call_args
    assert call_args[1]["body"]["name"] == "new_folder"
    assert call_args[1]["body"]["mimeType"] == "application/vnd.google-apps.folder"


# ============================================================
# _ensure_folder_path テスト
# ============================================================


def test_ensure_folder_path_all_existing(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """全フォルダが存在する場合、既存のIDが返されること。

    Given:
        - folder/subfolder のパスが全て存在する

    When:
        - _ensure_folder_path(["folder", "subfolder"]) を実行

    Then:
        - 新規作成されず、既存のフォルダIDが返されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value

    # 1回目: folder検索 → folder_id_1
    # 2回目: subfolder検索 → folder_id_2
    mock_list_req.execute.side_effect = [
        {"files": [{"id": "folder_id_1"}]},
        {"files": [{"id": "folder_id_2"}]},
    ]

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._ensure_folder_path(["folder", "subfolder"])

    # Assert
    assert result == "folder_id_2"
    mock_files.create.assert_not_called()


def test_ensure_folder_path_all_new(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """全フォルダが存在しない場合、新規作成されること。

    Given:
        - folder/subfolder のパスが全て存在しない

    When:
        - _ensure_folder_path(["folder", "subfolder"]) を実行

    Then:
        - 2つのフォルダが新規作成され、最終フォルダIDが返されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # folder検索: なし → 作成
    # subfolder検索: なし → 作成
    mock_list_req.execute.side_effect = [
        {"files": []},
        {"files": []},
    ]
    mock_create_req.execute.side_effect = [
        {"id": "new_folder_id_1"},
        {"id": "new_folder_id_2"},
    ]

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._ensure_folder_path(["folder", "subfolder"])

    # Assert
    assert result == "new_folder_id_2"
    assert mock_files.create.call_count == 2


def test_ensure_folder_path_partial_existing(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> None:
    """一部のフォルダのみ存在する場合、残りが新規作成されること。

    Given:
        - folder は存在するが subfolder は存在しない

    When:
        - _ensure_folder_path(["folder", "subfolder"]) を実行

    Then:
        - folder は既存、subfolder は新規作成されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # folder検索: あり
    # subfolder検索: なし → 作成
    mock_list_req.execute.side_effect = [
        {"files": [{"id": "existing_folder_id"}]},
        {"files": []},
    ]
    mock_create_req.execute.return_value = {"id": "new_subfolder_id"}

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    result = provider._ensure_folder_path(["folder", "subfolder"])

    # Assert
    assert result == "new_subfolder_id"
    mock_files.create.assert_called_once()


# ============================================================
# パス区切り付きアップロード テスト
# ============================================================


def test_upload_with_path_creates_folders_and_file(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
    test_file: str,
) -> None:
    """パス区切り付きファイル名で新規作成時、フォルダとファイルが作成されること。

    Given:
        - folder/sub/file.txt というパス
        - フォルダもファイルも存在しない

    When:
        - upload() を実行

    Then:
        - フォルダが作成され、ファイルがアップロードされること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # ファイル検索: folder検索 → なし
    # _ensure_folder_path: folder検索 → なし、folder作成
    # _ensure_folder_path: sub検索 → なし、sub作成
    mock_list_req.execute.side_effect = [
        {"files": []},  # ファイル検索時のフォルダ検索
        {"files": []},  # _ensure_folder_path: folder検索
        {"files": []},  # _ensure_folder_path: sub検索
    ]
    mock_create_req.execute.side_effect = [
        {"id": "folder_id"},
        {"id": "sub_id"},
    ]
    mock_create_req.next_chunk.return_value = (None, {"id": "file_id"})

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "folder/sub/file.txt")

    # Assert
    # フォルダ作成(2回) + ファイル作成(1回) = 3回
    assert mock_files.create.call_count == 3


def test_upload_with_path_updates_existing_file(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
    test_file: str,
) -> None:
    """パス区切り付きファイル名で既存更新時、適切なフォルダで検索されること。

    Given:
        - folder/sub/file.txt というパス
        - フォルダとファイルが存在する

    When:
        - upload() を実行

    Then:
        - files().update() が呼ばれること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_update_req = mock_files.update.return_value

    # _find_folder_path: folder検索 → あり
    # _find_folder_path: sub検索 → あり
    # _search_for_file: ファイル検索 → あり
    mock_list_req.execute.side_effect = [
        {"files": [{"id": "folder_id"}]},
        {"files": [{"id": "sub_id"}]},
        {"files": [{"id": "existing_file_id"}]},
    ]
    mock_update_req.next_chunk.return_value = (None, {"id": "existing_file_id"})

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "folder/sub/file.txt")

    # Assert
    mock_files.update.assert_called_once()
    mock_files.create.assert_not_called()


# ============================================================
# 後方互換性テスト
# ============================================================


def test_upload_without_path_works_as_before(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
    test_file: str,
) -> None:
    """スラッシュなしファイル名で従来通りの動作が維持されること。

    Given:
        - スラッシュなしのファイル名

    When:
        - upload() を実行

    Then:
        - ルートフォルダ直下にファイルが作成されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    mock_list_req.execute.return_value = {"files": []}
    mock_create_req.next_chunk.return_value = (None, {"id": "file_id"})

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "simple_file.txt")

    # Assert
    # ファイル作成のみ（フォルダ作成なし）
    mock_files.create.assert_called_once()
    call_args = mock_files.create.call_args
    assert call_args[1]["body"]["name"] == "simple_file.txt"
    assert call_args[1]["body"]["parents"] == ["root_folder"]
