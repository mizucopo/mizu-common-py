"""Google Drive API 呼び出しの共通リトライ処理。"""

import errno
import logging
import random
import ssl
import time
from collections.abc import Callable
from typing import TypeVar

import httplib2
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

_ResultT = TypeVar("_ResultT")

_RETRYABLE_ERRNOS = {
    errno.ETIMEDOUT,
    errno.EPIPE,
    errno.ECONNABORTED,
    errno.ECONNREFUSED,
    errno.ECONNRESET,
}


def execute_with_retry(
    operation: Callable[[], _ResultT],
    *,
    max_retries: int,
    stage: str,
    target: str,
) -> _ResultT:
    """一時障害が発生した Google Drive API 呼び出しを再試行する。"""
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as error:
            if not _is_retryable(error) or attempt == max_retries:
                raise

            retry_attempt = attempt + 1
            delay_seconds = random.random() * 2**retry_attempt
            logger.warning(
                "Google Drive retry scheduled: retry_attempt=%d max_retries=%d "
                "delay_seconds=%.1f stage=%s target=%s error_type=%s "
                "http_status=%s error=%s",
                retry_attempt,
                max_retries,
                delay_seconds,
                stage,
                target,
                type(error).__name__,
                _http_status(error),
                error,
            )
            time.sleep(delay_seconds)

    raise AssertionError("retry loop must return or raise")


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, HttpError):
        status = _http_status(error)
        return status == 429 or (status is not None and 500 <= status <= 599)

    if isinstance(
        error,
        (
            TimeoutError,
            ConnectionError,
            ssl.SSLError,
            httplib2.ServerNotFoundError,
        ),
    ):
        return True

    return isinstance(error, OSError) and error.errno in _RETRYABLE_ERRNOS


def _http_status(error: Exception) -> int | None:
    if not isinstance(error, HttpError):
        return None
    return int(error.resp.status)
