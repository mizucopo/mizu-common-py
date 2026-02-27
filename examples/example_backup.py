"""BackupManagerの使用例.

この例は以下を示します:
- tempfileを使用した一時ディレクトリでのバックアップ
- BackupManagerの基本的な使用方法

実行方法:
    uv run python examples/example_backup.py

前提条件:
    なし（認証不要）
"""

import tempfile
from pathlib import Path

from mizu_common import BackupManager


def main() -> None:
    """バックアップのデモを実行する."""
    # 一時ディレクトリを作成してデモデータを準備
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # ソースディレクトリを作成
        source_dir = tmpdir_path / "source"
        source_dir.mkdir()

        # デモファイルを作成
        (source_dir / "file1.txt").write_text("Hello, World!")
        (source_dir / "file2.txt").write_text("Backup demo")

        # サブディレクトリも作成
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested file")

        print(f"ソースディレクトリ: {source_dir}")
        print("内容:")
        for item in source_dir.rglob("*"):
            print(f"  {item.relative_to(source_dir)}")

        # バックアップを作成
        backup_dir = tmpdir_path / "backups"
        backup_path = backup_dir / "backup.zip"

        print(f"\nバックアップを作成中: {backup_path}")
        manager = BackupManager(src_dirpath=str(source_dir))
        manager.backup(destination_path=str(backup_path))

        # バックアップ結果を確認
        print(f"\nバックアップ完了: {backup_path.exists()}")
        print(f"ファイルサイズ: {backup_path.stat().st_size} bytes")

        # バックアップの内容を確認（zipfileで検証）
        import zipfile

        with zipfile.ZipFile(backup_path, "r") as zf:
            print("\nバックアップの内容:")
            for name in zf.namelist():
                print(f"  {name}")


if __name__ == "__main__":
    main()
