"""非同期リトライ設定のデータクラス."""

from dataclasses import dataclass


@dataclass
class RetryConfig:
    """リトライ設定.

    Attributes:
        count: リトライ回数（0=リトライなし）。初回実行後の追加試行回数。
        interval: リトライ間隔（秒）。
    """

    count: int
    interval: float

    def __post_init__(self) -> None:
        if self.count < 0:
            msg = f"count must be >= 0, got {self.count}"
            raise ValueError(msg)
        if self.interval <= 0:
            msg = f"interval must be > 0, got {self.interval}"
            raise ValueError(msg)
