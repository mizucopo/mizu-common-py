"""他のインスタンスが既に実行中の場合の例外."""

from pathlib import Path


class AlreadyRunningError(Exception):
    """他のインスタンスが既に実行中の場合の例外.

    Attributes:
        lock_path: ロックファイルのパス
    """

    def __init__(self, message: str, lock_path: Path | None = None) -> None:
        """例外を初期化する.

        Args:
            message: エラーメッセージ
            lock_path: ロックファイルのパス
        """
        super().__init__(message)
        self._lock_path = lock_path

    @property
    def lock_path(self) -> Path | None:
        """ロックファイルのパスを取得する."""
        return self._lock_path
