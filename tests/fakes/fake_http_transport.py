from __future__ import annotations

from tests.fakes.fake_request import FakeRequest
from tests.fakes.fake_response import FakeResponse


class FakeHttpTransport:
    """requests.post のfake実装。送信内容を記録して検証可能にする。"""

    def __init__(
        self,
        status_code: int = 204,
        text: str = "",
        responses: list[tuple[int, str]] | None = None,
    ) -> None:
        self.requests: list[FakeRequest] = []
        self._status_code = status_code
        self._text = text
        self._responses = responses
        self._call_index = 0

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append(FakeRequest(url=url, **kwargs))  # type: ignore[arg-type]
        if self._responses is not None:
            idx = min(self._call_index, len(self._responses) - 1)
            status, text = self._responses[idx]
            self._call_index += 1
            return FakeResponse(status_code=status, text=text)
        return FakeResponse(status_code=self._status_code, text=self._text)

    @property
    def last_request(self) -> FakeRequest:
        return self.requests[-1]

    @property
    def request_count(self) -> int:
        return len(self.requests)
