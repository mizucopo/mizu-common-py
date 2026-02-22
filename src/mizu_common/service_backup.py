"""サービスバックアッププロバイダモジュール。"""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


class ServiceBackup:
    """ディレクトリのバックアップを行うサービスバックアッププロバイダ。"""

    def __init__(self, src_dirpath: str) -> None:
        """サービスバックアッププロバイダを初期化する。

        Args:
            src_dirpath (str): バックアップ対象のソースディレクトリパス。
        """
        self.src_dirpath = src_dirpath

    def backup(self, destination_path: str) -> None:
        """ディレクトリをzipアーカイブにバックアップする。

        Args:
            destination_path (str): バックアップアーカイブを保存するパス
                （ファイル名を含む）。
        """
        backup_dir = os.path.dirname(destination_path)
        os.makedirs(backup_dir, exist_ok=True)

        base_name_without_extension = os.path.splitext(destination_path)[0]
        try:
            shutil.make_archive(
                base_name=base_name_without_extension,
                format="zip",
                root_dir=self.src_dirpath,
            )
        except Exception as e:
            logger.error(f"'{self.src_dirpath}' のバックアップに失敗: {e}")
            raise
