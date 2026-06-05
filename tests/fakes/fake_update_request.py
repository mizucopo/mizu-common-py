from __future__ import annotations

from typing import Any

from tests.fakes.upload_record import UploadRecord


class FakeUpdateRequest:
    """files().update(fileId=..., media_body=...).next_chunk() のfake。"""

    def __init__(self, service: Any, kwargs: dict[str, Any]) -> None:
        self._service = service
        self._kwargs = kwargs

    def next_chunk(self, **_kwargs: object) -> tuple[None, dict[str, str]]:
        file_id = self._kwargs.get("fileId", "")

        try:
            self._service._track_upload_enter()
            with self._service._state_lock:
                metadata = self._service._lookup_by_id(file_id)
                self._service.history.append(
                    UploadRecord(
                        name=metadata.get("name", ""),
                        parent_id=metadata.get("parent_id", ""),
                        operation="update_file",
                        id=file_id,
                    )
                )
        finally:
            self._service._track_upload_exit()

        return (None, {"id": file_id})
