"""ファイルロックユーティリティ.

二重起動防止のためのファイルロック機能を提供する。
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

import portalocker
from portalocker import LockFlags

from mizu_common.exceptions.already_running_error import AlreadyRunningError
from mizu_common.exceptions.stale_lock_error import StaleLockError


class LockManager:
    """ファイルロック管理クラス."""

    def __init__(
        self,
        lock_dir: Path,
        lock_filename: str = ".app.lock",
        stale_hours: int = 3,
    ) -> None:
        """ロックマネージャを初期化する.

        Args:
            lock_dir: ロックファイルを配置するディレクトリ
            lock_filename: ロックファイル名
            stale_hours: ロックファイルが古いと判断する時間（時間単位）
        """
        self._lock_path = lock_dir / lock_filename
        self._stale_hours = stale_hours

    @property
    def lock_path(self) -> Path:
        """ロックファイルのパスを取得する."""
        return self._lock_path

    def _is_stale(self) -> bool:
        """ロックファイルが古いかどうかを確認する.

        Returns:
            ロックファイルの更新時刻がstale_hours時間以上前の場合はTrue
        """
        if not self._lock_path.exists():
            return False

        try:
            mtime = self._lock_path.stat().st_mtime
            age_hours = (time.time() - mtime) / 3600
            return age_hours >= self._stale_hours
        except OSError:
            return False

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """アプリケーションロックを取得する.

        ロックファイルを作成し、排他ロックを取得する。
        古いロックファイル（stale_hours時間以上前）が存在する場合は
        StaleLockErrorを発生させる。
        新しいロックファイルが存在する場合は、AlreadyRunningErrorを発生させる。

        Yields:
            None

        Raises:
            StaleLockError: 古いロックファイルが存在する場合
            AlreadyRunningError: 他のインスタンスが実行中の場合
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        # まずロック取得を試みる
        lock = portalocker.Lock(
            self._lock_path,
            mode="a",  # 追記モード（存在しない場合は作成、存在する場合は維持）
            flags=LockFlags.EXCLUSIVE | LockFlags.NON_BLOCKING,
        )

        try:
            lock.acquire()
        except portalocker.exceptions.AlreadyLocked:
            # ロック取得失敗時のみ、Staleかどうかをチェック
            if self._is_stale():
                raise StaleLockError(
                    f"Stale lock file detected (older than {self._stale_hours} hours): "
                    f"{self._lock_path}"
                ) from None
            raise AlreadyRunningError(
                f"Another instance is already running. Lock file: {self._lock_path}",
                lock_path=self._lock_path,
            ) from None

        try:
            yield
        finally:
            lock.release()
            with suppress(OSError):
                self._lock_path.unlink()

    def release(self) -> None:
        """ロックファイルを削除する.

        ロックファイルが存在する場合に削除する。
        このメソッドは他のプロセスがロックを保持しているかどうかにかかわらず、
        ファイルを削除する。

        Note:
            通常は acquire() コンテキストマネージャの使用を推奨。
            このメソッドは緊急時のクリーンアップ用途。
        """
        with suppress(OSError):
            self._lock_path.unlink()

    def is_locked(self) -> bool:
        """ロックファイルが存在するかどうかを確認する.

        Returns:
            ロックファイルが存在する場合はTrue
        """
        return self._lock_path.exists()
