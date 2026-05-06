from __future__ import annotations


class FakeResponse:
    """HTTPレスポンスのfake。"""

    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text
