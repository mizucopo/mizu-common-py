"""ServiceBackupプロバイダのテスト。"""

import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from mizu_common.service_backup import ServiceBackup


def test_creates_zip_archive_from_source_directory() -> None:
    """ソースディレクトリの全ファイルを含むzipアーカイブが作成されること.

    Given:
        - ソースディレクトリに複数のファイルとサブディレクトリが存在する
        - 空ディレクトリも含まれる
        - バックアップ先に既存のアーカイブファイルが存在する場合がある

    When:
        - ServiceBackup.backup() を実行

    Then:
        - zipアーカイブが作成される
        - アーカイブにすべてのファイルとサブディレクトリ内のファイルが含まれる
        - 既存のアーカイブがある場合は上書きされる
        - 上書きされたアーカイブに新しいファイル内容が含まれる
    """
    # Arrange: サンプルファイルを含む一時ソースディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        src_dir = Path(temp_dir) / "source"
        src_dir.mkdir()

        # テスト用ファイルを作成
        (src_dir / "file1.txt").write_text("Content 1")
        (src_dir / "file2.txt").write_text("Content 2")
        (src_dir / "subdir").mkdir()
        (src_dir / "subdir" / "file3.txt").write_text("Content 3")
        (src_dir / "empty_dir").mkdir()  # 空ディレクトリ

        backup_dir = Path(temp_dir) / "backup"
        backup_path = backup_dir / "archive.zip"

        backup = ServiceBackup(src_dirpath=str(src_dir))

        # Act: バックアップを実行
        backup.backup(str(backup_path))

        # Assert: zipアーカイブが正しく作成されたことを検証
        assert backup_path.exists(), "バックアップアーカイブが作成されること"

        with zipfile.ZipFile(backup_path) as zip_file:
            namelist = sorted(zip_file.namelist())
            # 期待されるすべてのファイルが存在することを検証
            assert "file1.txt" in namelist
            assert "file2.txt" in namelist
            assert "subdir/file3.txt" in namelist

            # ファイルの内容を検証
            assert zip_file.read("file1.txt") == b"Content 1"
            assert zip_file.read("file2.txt") == b"Content 2"
            assert zip_file.read("subdir/file3.txt") == b"Content 3"

            # 注: 空ディレクトリはプラットフォームやPythonバージョンによって
            # 含まれる場合と含まれない場合がある（shutil.make_archiveの挙動）

        # 異なる内容で新しいアーカイブを作成し、上書き動作を検証
        (src_dir / "file4.txt").write_text("Content 4")
        backup.backup(str(backup_path))

        with zipfile.ZipFile(backup_path) as zip_file:
            assert "file4.txt" in zip_file.namelist()
            assert zip_file.read("file4.txt") == b"Content 4"


def test_propagates_filesystem_errors_during_backup(mocker: Any) -> None:
    """アーカイブ作成中のファイルシステムエラーが呼び出し元に伝播されること.

    Given:
        - ソースディレクトリが存在する
        - shutil.make_archiveがOSErrorをスローする

    When:
        - ServiceBackup.backup() を実行

    Then:
        - OSErrorが呼び出し元に伝播される
    """
    # Arrange: ソースディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        src_dir = Path(temp_dir) / "source"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("Content")

        backup_path = Path(temp_dir) / "backup" / "archive.zip"

        backup = ServiceBackup(src_dirpath=str(src_dir))

        # shutil.make_archiveをモックしてファイルシステムエラーをシミュレート
        mock_make_archive = mocker.patch(
            "mizu_common.service_backup.shutil.make_archive"
        )
        mock_make_archive.side_effect = OSError("Permission denied")

        # Act & Assert: エラーが伝播されること
        with pytest.raises(OSError, match="Permission denied"):
            backup.backup(str(backup_path))
