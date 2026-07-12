from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from tests.fakes.upload_record import UploadRecord

if TYPE_CHECKING:
    pass

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class FakeDriveService:
    """Google Drive API の fake 実装。"""

    def __init__(self, root_folder_id: str = "root_folder") -> None:
        self.root_folder_id = root_folder_id

        self._folders: dict[tuple[str, str], dict[str, str]] = {}
        self._files: dict[tuple[str, str], dict[str, str]] = {}
        self._by_id: dict[str, dict[str, str]] = {}
        self._id_counter = 0
        self._state_lock = threading.Lock()

        self.history: list[UploadRecord] = []

        self._list_errors: list[Exception] = []
        self._upload_errors: list[Exception] = []
        self._list_attempts = 0
        self._upload_attempts = 0

        # 並行性追跡（アップロード用）
        self._upload_first_entered: threading.Event | None = None
        self._upload_both_entered: threading.Event | None = None
        self._upload_can_complete: threading.Event | None = None
        self._upload_entered_count = 0
        self._upload_concurrent = 0
        self._upload_max_concurrent = 0
        self._upload_count_lock = threading.Lock()

        # 並行性追跡（フォルダ作成用）
        self._folder_first_entered: threading.Event | None = None
        self._folder_both_entered: threading.Event | None = None
        self._folder_can_complete: threading.Event | None = None
        self._folder_entered_count = 0
        self._folder_concurrent = 0
        self._folder_max_concurrent = 0
        self._folder_count_lock = threading.Lock()

    # --- Seed API ---

    def seed_folder(
        self, name: str, parent_id: str, folder_id: str | None = None
    ) -> str:
        with self._state_lock:
            fid = folder_id or self._next_id()
            entry = {"id": fid, "name": name, "parent_id": parent_id}
            self._folders[(parent_id, name)] = entry
            self._by_id[fid] = entry
            return fid

    def seed_file(self, name: str, parent_id: str, file_id: str | None = None) -> str:
        with self._state_lock:
            fid = file_id or self._next_id()
            entry = {"id": fid, "name": name, "parent_id": parent_id}
            self._files[(parent_id, name)] = entry
            self._by_id[fid] = entry
            return fid

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"id_{self._id_counter}"

    def _lookup_by_id(self, file_id: str) -> dict[str, str]:
        return self._by_id[file_id]

    # --- エラー注入 ---

    def inject_list_error(self, error: Exception) -> None:
        self._list_errors.append(error)

    def inject_upload_error(self, error: Exception) -> None:
        self._upload_errors.append(error)

    def _consume_upload_error(self) -> None:
        with self._state_lock:
            self._upload_attempts += 1
            if self._upload_errors:
                raise self._upload_errors.pop(0)

    # --- 履歴プロパティ ---

    @property
    def created_files(self) -> list[UploadRecord]:
        with self._state_lock:
            snapshot = list(self.history)
        return [r for r in snapshot if r.operation == "create_file"]

    @property
    def created_folders(self) -> list[UploadRecord]:
        with self._state_lock:
            snapshot = list(self.history)
        return [r for r in snapshot if r.operation == "create_folder"]

    @property
    def updated_files(self) -> list[UploadRecord]:
        with self._state_lock:
            snapshot = list(self.history)
        return [r for r in snapshot if r.operation == "update_file"]

    @property
    def max_concurrent_uploads(self) -> int:
        with self._upload_count_lock:
            return self._upload_max_concurrent

    @property
    def list_attempts(self) -> int:
        with self._state_lock:
            return self._list_attempts

    @property
    def upload_attempts(self) -> int:
        with self._state_lock:
            return self._upload_attempts

    @property
    def max_concurrent_folder_creates(self) -> int:
        with self._folder_count_lock:
            return self._folder_max_concurrent

    # --- API entry point ---

    def files(self) -> Any:
        from tests.fakes.fake_files_resource import FakeFilesResource

        return FakeFilesResource(self)

    # --- 並行性追跡（アップロード） ---

    def _track_upload_enter(self) -> None:
        with self._upload_count_lock:
            self._upload_concurrent += 1
            self._upload_max_concurrent = max(
                self._upload_max_concurrent, self._upload_concurrent
            )
            self._upload_entered_count += 1
            if self._upload_first_entered is not None:
                self._upload_first_entered.set()
            if (
                self._upload_both_entered is not None
                and self._upload_entered_count >= 2
            ):
                self._upload_both_entered.set()
        if self._upload_can_complete is not None and not self._upload_can_complete.wait(
            timeout=5.0
        ):
            raise TimeoutError(
                "FakeDriveService: _upload_can_complete がタイムアウトしました"
            )

    def _track_upload_exit(self) -> None:
        with self._upload_count_lock:
            self._upload_concurrent -= 1

    # --- 並行性追跡（フォルダ作成） ---

    def _track_folder_enter(self) -> None:
        with self._folder_count_lock:
            self._folder_concurrent += 1
            self._folder_max_concurrent = max(
                self._folder_max_concurrent, self._folder_concurrent
            )
            self._folder_entered_count += 1
            if self._folder_first_entered is not None:
                self._folder_first_entered.set()
            if (
                self._folder_both_entered is not None
                and self._folder_entered_count >= 2
            ):
                self._folder_both_entered.set()
        if self._folder_can_complete is not None and not self._folder_can_complete.wait(
            timeout=5.0
        ):
            raise TimeoutError(
                "FakeDriveService: _folder_can_complete がタイムアウトしました"
            )

    def _track_folder_exit(self) -> None:
        with self._folder_count_lock:
            self._folder_concurrent -= 1
