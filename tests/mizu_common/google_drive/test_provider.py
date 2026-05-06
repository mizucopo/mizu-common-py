"""GoogleDriveProvider のアップロード機能のテスト."""

import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

from mizu_common.google_drive.provider import GoogleDriveProvider
from tests.fakes.fake_drive_service import FakeDriveService


def _make_provider(
    folder_id: str = "test_folder",
) -> tuple[GoogleDriveProvider, FakeDriveService]:
    """テスト用の GoogleDriveProvider と FakeDriveService を作成する."""
    mock_creds = MagicMock()
    mock_creds.token = "mock_token"
    fake = FakeDriveService(root_folder_id=folder_id)
    provider = GoogleDriveProvider(
        folder_id=folder_id,
        credentials=mock_creds,
        drive_service=fake,
    )
    return provider, fake


@pytest.fixture
def test_file(tmp_path: Any) -> str:
    """テスト用の一時ファイルが作成されること."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return str(file_path)


@pytest.mark.parametrize(
    "seed_existing,expected_operation",
    [
        (False, "create_file"),  # 新規作成
        (True, "update_file"),  # 既存更新
    ],
    ids=["新規作成", "既存更新"],
)
def test_upload_delegates_to_correct_api_method(
    test_file: str,
    seed_existing: bool,
    expected_operation: str,
) -> None:
    """同名ファイルの有無に応じて適切なAPIメソッドが呼ばれること.

    Arrange:
        FakeDriveService を用意する。
        seed_existing が True の場合、同名ファイルを事前に登録する。

    Act:
        GoogleDriveProvider.upload() を実行する。

    Assert:
        ファイルが存在しない場合: create_file が記録されること。
        ファイルが存在する場合: update_file が記録されること。
    """
    # Arrange
    provider, fake = _make_provider()
    if seed_existing:
        fake.seed_file("test.txt", "test_folder")

    # Act
    provider.upload(test_file, "test.txt")

    # Assert
    if expected_operation == "create_file":
        assert len(fake.created_files) == 1
        assert len(fake.updated_files) == 0
    else:
        assert len(fake.updated_files) == 1
        assert len(fake.created_files) == 0


def test_upload_with_path_creates_folders_and_file(test_file: str) -> None:
    """パス区切り付きファイル名で新規作成時、フォルダとファイルが作成されること.

    Arrange:
        folder/sub/file.txt というパスを用意する。
        フォルダもファイルも存在しない状態にする。

    Act:
        upload() を実行する。

    Assert:
        フォルダが作成され、ファイルがアップロードされること。
    """
    # Arrange
    provider, fake = _make_provider(folder_id="root_folder")

    # Act
    provider.upload(test_file, "folder/sub/file.txt")

    # Assert
    assert len(fake.created_folders) == 2  # folder + sub
    assert len(fake.created_files) == 1  # file.txt


def test_upload_with_path_updates_existing_file(test_file: str) -> None:
    """パス区切り付きファイル名で既存更新時、適切なフォルダで検索されること.

    Arrange:
        folder/sub/file.txt というパスを用意する。
        フォルダとファイルが存在する状態にする。

    Act:
        upload() を実行する。

    Assert:
        update_file が記録されること。
    """
    # Arrange
    provider, fake = _make_provider(folder_id="root_folder")
    folder_id = fake.seed_folder("folder", "root_folder")
    sub_id = fake.seed_folder("sub", folder_id)
    fake.seed_file("file.txt", sub_id)

    # Act
    provider.upload(test_file, "folder/sub/file.txt")

    # Assert
    assert len(fake.updated_files) == 1
    assert len(fake.created_files) == 0


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
        sanitize_name() を実行する。

    Assert:
        期待されるサニタイズ結果が返されること。
    """
    # Arrange
    # Act
    result = GoogleDriveProvider.sanitize_name(raw_name)

    # Assert
    assert result == expected


def test_upload_sanitizes_folder_and_file_names(test_file: str) -> None:
    """パス区切り付きファイル名でサニタイズが適用されること.

    Arrange:
        folder:name/file?.txt というパス（禁止文字を含む）を用意する。
        フォルダもファイルも存在しない状態にする。

    Act:
        upload() を実行する。

    Assert:
        サニタイズされた名前でフォルダとファイルが作成されること。
    """
    # Arrange
    provider, fake = _make_provider(folder_id="root_folder")

    # Act
    provider.upload(test_file, "folder:name/file?.txt")

    # Assert
    assert len(fake.created_folders) == 1
    assert fake.created_folders[0].name == "folder_name"
    assert len(fake.created_files) == 1
    assert fake.created_files[0].name == "file_.txt"


def test_concurrent_upload_of_different_files_runs_in_parallel(
    test_file: str,
) -> None:
    """異なるファイルの並行アップロードが並列実行されること.

    Arrange:
        異なる2つのファイル名を用意する。
        FakeDriveService の並行性追跡イベントを設定する。

    Act:
        2つのスレッドで異なるファイルのアップロードを並行開始する。

    Assert:
        両方のアップロードが同時に実行されること。
    """
    # Arrange
    provider, fake = _make_provider()

    both_entered = threading.Event()
    can_complete = threading.Event()
    fake._upload_both_entered = both_entered
    fake._upload_can_complete = can_complete

    start_gate = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker(filename: str) -> None:
        try:
            start_gate.wait(timeout=5.0)
            provider.upload(test_file, filename)
        except BaseException as e:
            errors.append(e)

    # Act
    thread1 = threading.Thread(target=worker, args=("file1.txt",))
    thread2 = threading.Thread(target=worker, args=("file2.txt",))
    thread1.start()
    thread2.start()

    sync_ok = False
    try:
        sync_ok = both_entered.wait(timeout=5.0)
    finally:
        can_complete.set()
        thread1.join(timeout=5.0)
        thread2.join(timeout=5.0)

    # Assert
    assert not thread1.is_alive()
    assert not thread2.is_alive()
    assert errors == []
    assert sync_ok, "両スレッドが upload に到達しませんでした"
    assert fake.max_concurrent_uploads == 2


def test_concurrent_upload_of_same_file_runs_serially(
    test_file: str,
) -> None:
    """同じファイルの並行アップロードが直列実行されること.

    Arrange:
        同じファイル名への2つのアップロードを用意する。
        FakeDriveService の並行性追跡イベントを設定する。

    Act:
        2つのスレッドで同じファイルのアップロードを並行開始する。

    Assert:
        同時に実行されるアップロードが最大1つであること。
    """
    # Arrange
    provider, fake = _make_provider()

    first_entered = threading.Event()
    both_entered = threading.Event()
    can_complete = threading.Event()
    fake._upload_first_entered = first_entered
    fake._upload_both_entered = both_entered
    fake._upload_can_complete = can_complete

    start_gate = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker(filename: str) -> None:
        try:
            start_gate.wait(timeout=5.0)
            provider.upload(test_file, filename)
        except BaseException as e:
            errors.append(e)

    # Act
    thread1 = threading.Thread(target=worker, args=("same.txt",))
    thread2 = threading.Thread(target=worker, args=("same.txt",))
    thread1.start()
    thread2.start()

    first_ok = False
    not_both = False
    try:
        first_ok = first_entered.wait(timeout=5.0)
        not_both = not both_entered.wait(timeout=0.3)
    finally:
        can_complete.set()
        thread1.join(timeout=5.0)
        thread2.join(timeout=5.0)

    # Assert
    assert not thread1.is_alive()
    assert not thread2.is_alive()
    assert errors == []
    assert first_ok
    assert not_both, "直列化されていません"
    assert fake.max_concurrent_uploads == 1


def test_upload_releases_file_lock_on_exception(test_file: str) -> None:
    """例外発生後も同じファイルのアップロードが再実行されること.

    Arrange:
        1回目のアップロードで例外が発生するようエラーを注入する。

    Act:
        1回目の upload() で例外が発生する。
        2回目の upload() を実行する。

    Assert:
        2回目のアップロードが正常に完了すること。
    """
    # Arrange
    provider, fake = _make_provider()
    fake.inject_list_error(RuntimeError("API Error"))

    # Act & Assert
    with pytest.raises(RuntimeError, match="API Error"):
        provider.upload(test_file, "test.txt")

    # 例外後も同じファイルのアップロードが成功することで、ロック解放が検証される
    provider.upload(test_file, "test.txt")


def test_file_lock_is_removed_after_upload(test_file: str) -> None:
    """アップロード完了後に同じファイルの再アップロードが直ちに実行されること.

    Arrange:
        FakeDriveService を用意する。

    Act:
        upload() を2回連続で実行する。

    Assert:
        両方のアップロードが正常に完了すること。
    """
    # Arrange
    provider, fake = _make_provider()

    # Act
    provider.upload(test_file, "test.txt")
    provider.upload(test_file, "test.txt")

    # Assert
    # 1回目は新規作成、2回目は既存ファイルの更新として記録される
    assert len(fake.created_files) == 1
    assert len(fake.updated_files) == 1


def test_concurrent_upload_to_same_folder_path_does_not_create_duplicate_folders(
    test_file: str,
) -> None:
    """同じフォルダパスへの並行アップロードで重複フォルダが作成されないこと.

    Arrange:
        同じフォルダパス(folder/sub)を使用する異なる2つのファイルを用意する。
        FakeDriveService のフォルダ作成並行性追跡イベントを設定する。

    Act:
        2つのスレッドで異なるファイルを同じフォルダに並行アップロードする。

    Assert:
        同時に実行されるフォルダ作成処理が最大1つであること。
    """
    # Arrange
    provider, fake = _make_provider(folder_id="root_folder")

    first_entered = threading.Event()
    both_entered = threading.Event()
    can_complete = threading.Event()
    fake._folder_first_entered = first_entered
    fake._folder_both_entered = both_entered
    fake._folder_can_complete = can_complete

    start_gate = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker(filename: str) -> None:
        try:
            start_gate.wait(timeout=5.0)
            provider.upload(test_file, f"folder/sub/{filename}")
        except BaseException as e:
            errors.append(e)

    # Act
    thread1 = threading.Thread(target=worker, args=("file1.txt",))
    thread2 = threading.Thread(target=worker, args=("file2.txt",))
    thread1.start()
    thread2.start()

    first_ok = False
    not_both = False
    try:
        first_ok = first_entered.wait(timeout=5.0)
        not_both = not both_entered.wait(timeout=0.3)
    finally:
        can_complete.set()
        thread1.join(timeout=5.0)
        thread2.join(timeout=5.0)

    # Assert
    assert not thread1.is_alive()
    assert not thread2.is_alive()
    assert errors == []
    assert first_ok
    assert not_both, "フォルダ作成が直列化されていません"
    assert fake.max_concurrent_folder_creates == 1

    # フォルダ作成は2回（folder + sub の各スレッドで各1回ずつ）
    assert len(fake.created_folders) == 2
    # 親子関係の検証: (root_folder, folder) と (folder_id, sub) の組み合わせ
    parent_child_pairs = {(f.parent_id, f.name) for f in fake.created_folders}
    assert (fake.root_folder_id, "folder") in parent_child_pairs
    # sub フォルダの親は folder の ID
    folder_records = [f for f in fake.created_folders if f.name == "folder"]
    assert len(folder_records) == 1
    assert (folder_records[0].id, "sub") in parent_child_pairs


def test_folder_lock_is_removed_after_upload(test_file: str) -> None:
    """アップロード完了後に同じフォルダパスの再アップロードが直ちに実行されること.

    Arrange:
        FakeDriveService を用意する。

    Act:
        同じフォルダパスへの upload() を2回連続で実行する。

    Assert:
        両方のアップロードが正常に完了すること。
    """
    # Arrange
    provider, fake = _make_provider(folder_id="root_folder")

    # Act
    provider.upload(test_file, "folder/sub/file1.txt")
    provider.upload(test_file, "folder/sub/file2.txt")

    # Assert
    assert len(fake.created_files) == 2
