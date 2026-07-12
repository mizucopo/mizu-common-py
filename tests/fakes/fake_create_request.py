from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tests.fakes.upload_record import UploadRecord

if TYPE_CHECKING:
    pass

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class FakeCreateRequest:
    """files().create(body=...).execute() と .next_chunk() のfake。"""

    def __init__(self, service: Any, kwargs: dict[str, Any]) -> None:
        self._service = service
        self._kwargs = kwargs

    def execute(self) -> dict[str, str]:
        body = self._kwargs.get("body", {})
        name = body.get("name", "")
        parent_id = body.get("parents", [""])[0] if body.get("parents") else ""

        try:
            self._service._track_folder_enter()
            with self._service._state_lock:
                fid = self._service._next_id()
                entry = {"id": fid, "name": name, "parent_id": parent_id}
                self._service._folders[(parent_id, name)] = entry
                self._service._by_id[fid] = entry
                self._service.history.append(
                    UploadRecord(
                        name=name,
                        parent_id=parent_id,
                        operation="create_folder",
                        id=fid,
                    )
                )
                if self._service._folder_create_response_errors:
                    raise self._service._folder_create_response_errors.pop(0)
        finally:
            self._service._track_folder_exit()

        return {"id": fid}

    def next_chunk(self, **_kwargs: object) -> tuple[None, dict[str, str]]:
        self._service._consume_upload_error()
        body = self._kwargs.get("body", {})
        name = body.get("name", "")
        parent_id = body.get("parents", [""])[0] if body.get("parents") else ""

        try:
            self._service._track_upload_enter()
            with self._service._state_lock:
                fid = self._service._next_id()
                entry = {"id": fid, "name": name, "parent_id": parent_id}
                self._service._files[(parent_id, name)] = entry
                self._service._by_id[fid] = entry
                self._service.history.append(
                    UploadRecord(
                        name=name,
                        parent_id=parent_id,
                        operation="create_file",
                        id=fid,
                    )
                )
        finally:
            self._service._track_upload_exit()

        return (None, {"id": fid})
