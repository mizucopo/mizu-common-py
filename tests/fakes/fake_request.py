from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeRequest:
    """HTTPリクエストの記録。"""

    url: str
    json: dict[str, object] | None = None
    timeout: int | None = None
