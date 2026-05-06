from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tests.fakes.fake_create_request import FakeCreateRequest
from tests.fakes.fake_list_request import FakeListRequest
from tests.fakes.fake_update_request import FakeUpdateRequest

if TYPE_CHECKING:
    pass


class FakeFilesResource:
    """service.files() の戻り値。"""

    def __init__(self, service: Any) -> None:
        self._service = service

    def list(self, **kwargs: object) -> FakeListRequest:
        return FakeListRequest(self._service, kwargs)

    def create(self, **kwargs: object) -> FakeCreateRequest:
        return FakeCreateRequest(self._service, kwargs)

    def update(self, **kwargs: object) -> FakeUpdateRequest:
        return FakeUpdateRequest(self._service, kwargs)
