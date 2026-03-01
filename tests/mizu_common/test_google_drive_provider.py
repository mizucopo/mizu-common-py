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


@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("file:name?.txt", "file_name_.txt"),  # 禁止文字の置換
        (".hidden.", "hidden"),  # 先頭・末尾のドット削除
        ("", "untitled"),  # 空文字列
        ("...", "untitled"),  # ドットのみ
        ("  .  ", "untitled"),  # スペースとドットのみ
        ("normal.txt", "normal.txt"),  # 正常なファイル名
    ],
    ids=[
        "禁止文字の置換",
        "先頭末尾ドット削除",
        "空文字列",
        "ドットのみ",
        "スペースとドットのみ",
        "正常なファイル名",
    ],
)
def test_sanitize_name_handles_various_inputs(raw_name: str, expected: str) -> None:
    """様々な入力に対してサニタイズが正しく適用されること。

    Given:
        - 様々なパターンのファイル名

    When:
        - sanitize_name() を実行

    Then:
        - 期待されるサニタイズ結果が返されること
    """
    # Act
    result = GoogleDriveProvider.sanitize_name(raw_name)

    # Assert
    assert result == expected


def test_upload_sanitizes_folder_and_file_names(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
    test_file: str,
) -> None:
    """パス区切り付きファイル名でサニタイズが適用されること。

    Given:
        - folder:name/file?.txt というパス（禁止文字を含む）
        - フォルダもファイルも存在しない

    When:
        - upload() を実行

    Then:
        - サニタイズされた名前でフォルダとファイルが作成されること
    """
    # Arrange
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value

    # ファイル検索: フォルダ検索 → なし
    # _ensure_folder_path: folder_name検索 → なし、作成
    mock_list_req.execute.side_effect = [
        {"files": []},  # _find_folder_path: folder:name検索
        {"files": []},  # _ensure_folder_path: folder_name検索
    ]
    mock_create_req.execute.side_effect = [
        {"id": "sanitized_folder_id"},
    ]
    mock_create_req.next_chunk.return_value = (None, {"id": "file_id"})

    provider = GoogleDriveProvider(
        folder_id="root_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )

    # Act
    provider.upload(test_file, "folder:name/file?.txt")

    # Assert
    # フォルダ作成時の名前を確認
    folder_create_call = mock_files.create.call_args_list[0]
    assert folder_create_call[1]["body"]["name"] == "folder_name"

    # ファイル作成時の名前を確認
    file_create_call = mock_files.create.call_args_list[1]
    assert file_create_call[1]["body"]["name"] == "file_.txt"
