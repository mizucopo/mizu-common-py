"""ファイルロックユーティリティのテスト."""

import os
from pathlib import Path

import pytest

from mizu_common.exceptions import AlreadyRunningError, StaleLockError
from mizu_common.lock_manager import LockManager


def test_acquire_lock_prevents_concurrent_access(tmp_path: Path) -> None:
    """acquireが二重起動を防止すること.

    Arrange:
        ロックを取得する。

    Act:
        同じロックを再度取得しようとする。

    Assert:
        AlreadyRunningErrorが発生すること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path)
    cm = lock_manager.acquire()
    cm.__enter__()

    try:
        # Act & Assert
        with pytest.raises(AlreadyRunningError):
            lock_manager.acquire().__enter__()
    finally:
        cm.__exit__(None, None, None)


def test_acquire_lock_releases_on_exit(tmp_path: Path) -> None:
    """acquireが終了時にロックを解放すること.

    Arrange:
        ロックを取得して解放する。

    Act:
        再度ロックを取得する。

    Assert:
        ロックが正常に取得できること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path)

    # Act
    with lock_manager.acquire():
        pass

    # Assert - should not raise
    with lock_manager.acquire():
        pass


def test_acquire_lock_raises_error_on_stale_file(tmp_path: Path) -> None:
    """古いロックファイルがある場合にStaleLockErrorが発生すること.

    Arrange:
        stale_hours=1を設定する。
        ロックファイルを作成し、mtimeを4時間前に設定する。

    Act:
        ロックを取得しようとする。

    Assert:
        StaleLockErrorが発生すること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path, stale_hours=1)
    lock_path = tmp_path / ".app.lock"
    lock_path.touch()
    # mtimeを4時間前に設定（stale_hours=1より古い）
    stale_time = os.path.getmtime(lock_path) - 4 * 3600
    os.utime(lock_path, (stale_time, stale_time))

    # Act & Assert
    with (
        pytest.raises(StaleLockError, match="Stale lock file detected"),
        lock_manager.acquire(),
    ):
        pass


def test_acquire_lock_raises_error_on_recent_file(tmp_path: Path) -> None:
    """新しいロックファイルがある場合はAlreadyRunningErrorすること.

    Arrange:
        stale_hours=1を設定する。
        ロックファイルを作成する。

    Act:
        ロックを取得しようとする。

    Assert:
        AlreadyRunningErrorが発生すること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path, stale_hours=1)
    lock_path = tmp_path / ".app.lock"
    lock_path.touch()

    # Act & Assert
    with (
        pytest.raises(AlreadyRunningError, match="Another instance"),
        lock_manager.acquire(),
    ):
        pass
