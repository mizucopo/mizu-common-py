"""ファイルロックユーティリティのテスト."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mizu_common.exceptions.already_running_error import AlreadyRunningError
from mizu_common.exceptions.stale_lock_error import StaleLockError
from mizu_common.lock_manager import LockManager


def test_acquire_lock_prevents_concurrent_access(tmp_path: Path) -> None:
    """acquireが二重起動を防止すること.

    Arrange:
        portalockerをモックして、2回目のロック取得でAlreadyLockedを発生させる。

    Act:
        同じロックを再度取得しようとする。

    Assert:
        AlreadyRunningErrorが発生すること。
    """
    # Arrange
    import portalocker.exceptions

    lock_manager = LockManager(lock_dir=tmp_path)

    with patch("mizu_common.lock_manager.portalocker.Lock") as mock_lock_class:
        mock_lock = MagicMock()
        mock_lock_class.return_value = mock_lock

        # 1回目は成功、2回目はAlreadyLocked
        mock_lock.acquire.side_effect = [None, portalocker.exceptions.AlreadyLocked()]

        # Act & Assert
        with lock_manager.acquire(), pytest.raises(AlreadyRunningError):
            lock_manager.acquire().__enter__()


def test_acquire_lock_releases_on_exit(tmp_path: Path) -> None:
    """acquireが終了時にロックを解放すること.

    Arrange:
        portalockerをモックする。

    Act:
        ロックを取得して解放した後、再度ロックを取得する。

    Assert:
        ロックが正常に取得・解放できること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path)

    with patch("mizu_common.lock_manager.portalocker.Lock") as mock_lock_class:
        mock_lock1 = MagicMock()
        mock_lock2 = MagicMock()
        mock_lock_class.side_effect = [mock_lock1, mock_lock2]

        # Act & Assert
        with lock_manager.acquire():
            pass

        # 2回目も正常に取得できること
        with lock_manager.acquire():
            pass

        # 各ロックが正しくacquire/releaseされたこと
        mock_lock1.acquire.assert_called_once()
        mock_lock1.release.assert_called_once()
        mock_lock2.acquire.assert_called_once()
        mock_lock2.release.assert_called_once()


def test_acquire_lock_raises_error_on_stale_file(tmp_path: Path) -> None:
    """古いロックファイルを他のプロセスが保持している場合にStaleLockErrorが発生すること.

    Arrange:
        portalockerをモックしてAlreadyLockedを発生させる。
        ロックファイルを作成し、mtimeを4時間前に設定する。

    Act:
        stale_hours=1のLockManagerでロックを取得しようとする。

    Assert:
        StaleLockErrorが発生すること。
    """
    # Arrange
    import portalocker.exceptions

    lock_path = tmp_path / ".app.lock"
    lock_path.touch()

    # mtimeを4時間前に設定
    stale_time = os.path.getmtime(lock_path) - 4 * 3600
    os.utime(lock_path, (stale_time, stale_time))

    lock_manager = LockManager(lock_dir=tmp_path, stale_hours=1)

    with patch("mizu_common.lock_manager.portalocker.Lock") as mock_lock_class:
        mock_lock = MagicMock()
        mock_lock_class.return_value = mock_lock
        mock_lock.acquire.side_effect = portalocker.exceptions.AlreadyLocked()

        # Act & Assert
        with pytest.raises(StaleLockError, match="Stale lock file detected"):
            lock_manager.acquire().__enter__()


def test_acquire_lock_raises_error_on_recent_file(tmp_path: Path) -> None:
    """新しいロックファイルを他のプロセスが保持している場合はAlreadyRunningErrorが発生すること.

    Arrange:
        portalockerをモックしてAlreadyLockedを発生させる。
        ロックファイルを新規作成する。

    Act:
        stale_hours=1のLockManagerでロックを取得しようとする。

    Assert:
        AlreadyRunningErrorが発生すること。
    """
    # Arrange
    import portalocker.exceptions

    lock_path = tmp_path / ".app.lock"
    lock_path.touch()

    lock_manager = LockManager(lock_dir=tmp_path, stale_hours=1)

    with patch("mizu_common.lock_manager.portalocker.Lock") as mock_lock_class:
        mock_lock = MagicMock()
        mock_lock_class.return_value = mock_lock
        mock_lock.acquire.side_effect = portalocker.exceptions.AlreadyLocked()

        # Act & Assert
        with pytest.raises(AlreadyRunningError, match="Another instance"):
            lock_manager.acquire().__enter__()
