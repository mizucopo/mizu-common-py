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


@pytest.fixture
def mock_gdrive_files(mock_gdrive_service: Any) -> tuple[Any, Any, Any]:
    """モック化された Google Drive files リソース.

    Returns:
        (mock_files, mock_list_req, mock_create_req) のタプル
    """
    mock_files = mock_gdrive_service.files.return_value
    mock_list_req = mock_files.list.return_value
    mock_create_req = mock_files.create.return_value
    return mock_files, mock_list_req, mock_create_req


@pytest.fixture
def gdrive_provider(
    mock_gdrive_credentials: Any,
    mock_gdrive_service: Any,
) -> GoogleDriveProvider:
    """テスト用の GoogleDriveProvider インスタンス."""
    return GoogleDriveProvider(
        folder_id="test_folder",
        credentials=mock_gdrive_credentials,
        drive_service=mock_gdrive_service,
    )


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
    """同名ファイルの有無に応じて適切なAPIメソッドが呼ばれること.

    Arrange:
        有効な認証情報を用意する。

    Act:
        GoogleDriveProvider.upload()を実行する。

    Assert:
        ファイルが存在しない場合: files().create()が呼ばれること。
        ファイルが存在する場合: files().update()が呼ばれること。
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
    """パス区切り付きファイル名で新規作成時、フォルダとファイルが作成されること.

    Arrange:
        folder/sub/file.txtというパスを用意する。
        フォルダもファイルも存在しない状態にする。

    Act:
        upload()を実行する。

    Assert:
        フォルダが作成され、ファイルがアップロードされること。
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
    """パス区切り付きファイル名で既存更新時、適切なフォルダで検索されること.

    Arrange:
        folder/sub/file.txtというパスを用意する。
        フォルダとファイルが存在する状態にする。

    Act:
        upload()を実行する。

    Assert:
        files().update()が呼ばれること。
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
    """様々な入力に対してサニタイズが正しく適用されること.

    Arrange:
        様々なパターンのファイル名を用意する。

    Act:
        sanitize_name()を実行する。

    Assert:
        期待されるサニタイズ結果が返されること。
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
    """パス区切り付きファイル名でサニタイズが適用されること.

    Arrange:
        folder:name/file?.txtというパス（禁止文字を含む）を用意する。
        フォルダもファイルも存在しない状態にする。

    Act:
        upload()を実行する。

    Assert:
        サニタイズされた名前でフォルダとファイルが作成されること。
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


def test_concurrent_upload_of_different_files_runs_in_parallel(
    mock_gdrive_files: tuple[Any, Any, Any],
    gdrive_provider: GoogleDriveProvider,
    test_file: str,
) -> None:
    """異なるファイルの並行アップロードが並列実行されること.

    Arrange:
        異なる2つのファイル名を用意する。
        アップロード処理をブロックするためのイベントを設定する。

    Act:
        2つのスレッドで異なるファイルのアップロードを並行開始する。

    Assert:
        両方のアップロードが同時に実行されること。
    """
    # Arrange
    import threading

    _, mock_list_req, mock_create_req = mock_gdrive_files

    mock_list_req.execute.return_value = {"files": []}

    # アップロードの進行を制御するためのイベント
    upload_started = threading.Event()
    can_complete = threading.Event()
    execution_order: list[str] = []

    def mock_next_chunk(*_: Any, **__: Any) -> tuple[Any, dict[str, str]]:
        upload_started.set()
        execution_order.append("started")
        can_complete.wait()  # 両方のスレッドがここに到達するまで待機
        return (None, {"id": "file_id"})

    mock_create_req.next_chunk.side_effect = mock_next_chunk

    provider = gdrive_provider

    results: list[str] = []
    errors: list[Exception] = []

    def upload_file1() -> None:
        try:
            provider.upload(test_file, "file1.txt")
            results.append("file1_done")
        except Exception as e:
            errors.append(e)

    def upload_file2() -> None:
        try:
            provider.upload(test_file, "file2.txt")
            results.append("file2_done")
        except Exception as e:
            errors.append(e)

    # Act
    thread1 = threading.Thread(target=upload_file1)
    thread2 = threading.Thread(target=upload_file2)

    thread1.start()
    thread2.start()

    # 両方のスレッドがアップロードを開始するまで待機
    # 並列実行されていれば、両方が next_chunk に到達できる
    upload_started.wait(timeout=5.0)

    # アップロード完了を許可
    can_complete.set()

    thread1.join(timeout=5.0)
    thread2.join(timeout=5.0)

    # Assert
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    assert len(results) == 2, "Both uploads should complete"


def test_concurrent_upload_of_same_file_runs_serially(
    mock_gdrive_files: tuple[Any, Any, Any],
    gdrive_provider: GoogleDriveProvider,
    test_file: str,
) -> None:
    """同じファイルの並行アップロードが直列実行されること.

    Arrange:
        同じファイル名への2つのアップロードを用意する。
        アップロード処理内で並行実行を検出するためのカウンターを設定する。

    Act:
        2つのスレッドで同じファイルのアップロードを並行開始する。

    Assert:
        同時に実行されるアップロードが最大1つであること。
    """
    # Arrange
    import threading

    _, mock_list_req, mock_create_req = mock_gdrive_files

    mock_list_req.execute.return_value = {"files": []}

    # 並行実行数を追跡
    concurrent_count = 0
    max_concurrent = 0
    count_lock = threading.Lock()
    can_proceed = threading.Event()

    # 両方のスレッドが開始したことを検知するカウンター
    started_count = 0
    started_lock = threading.Lock()
    both_started = threading.Event()

    def mock_next_chunk(*_: Any, **__: Any) -> tuple[Any, dict[str, str]]:
        nonlocal concurrent_count, max_concurrent

        with count_lock:
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)

        can_proceed.wait(timeout=5.0)

        with count_lock:
            concurrent_count -= 1

        return (None, {"id": "file_id"})

    mock_create_req.next_chunk.side_effect = mock_next_chunk

    provider = gdrive_provider

    results: list[str] = []
    errors: list[Exception] = []

    def upload_file() -> None:
        nonlocal started_count
        with started_lock:
            started_count += 1
            if started_count == 2:
                both_started.set()
        try:
            provider.upload(test_file, "same_file.txt")
            results.append("done")
        except Exception as e:
            errors.append(e)

    # Act
    thread1 = threading.Thread(target=upload_file)
    thread2 = threading.Thread(target=upload_file)

    thread1.start()
    thread2.start()

    # 両方のスレッドが開始したことを確認してから進行を許可
    both_started.wait(timeout=5.0)
    can_proceed.set()

    thread1.join(timeout=5.0)
    thread2.join(timeout=5.0)

    # Assert
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    assert len(results) == 2, "Both uploads should complete"
    assert max_concurrent == 1, (
        f"Expected max 1 concurrent upload, got {max_concurrent}"
    )


def test_upload_releases_file_lock_on_exception(
    mock_gdrive_files: tuple[Any, Any, Any],
    gdrive_provider: GoogleDriveProvider,
    test_file: str,
) -> None:
    """例外発生時でもファイルロックが解放されること.

    Arrange:
        例外を発生させるモックを設定する。

    Act:
        upload()を実行し、例外が発生する。

    Assert:
        例外が発生してもファイルロックが解放されること。
    """
    # Arrange
    _, mock_list_req, _ = mock_gdrive_files

    # 検索時に例外を発生させる
    mock_list_req.execute.side_effect = RuntimeError("API Error")

    # Act & Assert
    with pytest.raises(RuntimeError, match="API Error"):
        gdrive_provider.upload(test_file, "test.txt")

    # 例外発生後もファイルロックが解放されていることを確認
    file_lock = gdrive_provider._get_lock_for_file("test.txt")
    assert file_lock.locked() is False
