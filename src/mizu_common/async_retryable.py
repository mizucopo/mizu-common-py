"""非同期リトライ実行クラス."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from mizu_common.retry_config import RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncRetryable:
    """設定に基づいて非同期関数をリトライ実行する.

    Args:
        config: リトライ設定。
        transient_exceptions: リトライ対象の一時的例外のタプル。
    """

    def __init__(
        self,
        config: RetryConfig,
        transient_exceptions: tuple[type[Exception], ...] = (),
    ) -> None:
        self._config = config
        self._transient_exceptions = transient_exceptions

    async def execute(self, fn: Callable[[], Awaitable[T]]) -> T:
        """関数を実行し、一時的例外時はリトライする.

        Args:
            fn: 実行する非同期関数。

        Returns:
            関数の戻り値。

        Raises:
            Exception: 全試行失敗時は最後の一時的例外。
                一時的でない例外はリトライせず即座に送出。
        """
        last_error: Exception | None = None
        for attempt in range(self._config.count + 1):
            try:
                return await fn()
            except self._transient_exceptions as e:
                last_error = e
                if attempt < self._config.count:
                    logger.info(
                        "試行 %d/%d 失敗、%s秒後にリトライ: %s",
                        attempt + 1,
                        self._config.count + 1,
                        self._config.interval,
                        e,
                    )
                    await asyncio.sleep(self._config.interval)
                else:
                    logger.error(
                        "%d回試行後に失敗: %s",
                        self._config.count + 1,
                        e,
                    )
        assert last_error is not None, "unreachable: at least one attempt is guaranteed"
        raise last_error
