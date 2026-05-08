"""AsyncRetryableクラスのテスト."""

import asyncio
from typing import Any

import pytest

from mizu_common.async_retryable import AsyncRetryable
from mizu_common.retry_config import RetryConfig


class _TransientError(Exception):
    """テスト用の一時的エラー."""


class _NonTransientError(Exception):
    """テスト用の非一時的エラー."""


def test_execute_succeeds_on_first_attempt() -> None:
    """初回実行で成功した場合、結果が返されること.

    Arrange:
        常に成功する関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        結果が返されること。
        関数が1回だけ呼び出されること。
    """
    # Arrange
    call_count = 0

    async def _succeed() -> int:
        nonlocal call_count
        call_count += 1
        return 42

    retry = AsyncRetryable(
        config=RetryConfig(count=2, interval=1.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    result = asyncio.run(retry.execute(_succeed))

    # Assert
    assert result == 42
    assert call_count == 1


def test_execute_retries_and_succeeds_on_second_attempt(mocker: Any) -> None:
    """一時的エラー後にリトライして成功した場合、結果が返されること.

    Arrange:
        1回目は一時的エラー、2回目は成功する関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        結果が返されること。
        関数が2回呼び出されること。
        asyncio.sleepがintervalの値で1回呼び出されること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _TransientError("connection lost")
        return "ok"

    retry = AsyncRetryable(
        config=RetryConfig(count=2, interval=5.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    result = asyncio.run(retry.execute(_flaky))

    # Assert
    assert result == "ok"
    assert call_count == 2
    mock_sleep.assert_called_once_with(5.0)


def test_execute_raises_after_all_attempts_exhausted(mocker: Any) -> None:
    """全試行が一時的エラーで失敗した場合、最後の例外が送出されること.

    Arrange:
        常に一時的エラーを発生させる関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        最後の_TransientErrorが送出されること。
        関数が3回（count=2 + 初回）呼び出されること。
        asyncio.sleepが2回呼び出されること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _always_fail() -> None:
        nonlocal call_count
        call_count += 1
        raise _TransientError(f"fail-{call_count}")

    retry = AsyncRetryable(
        config=RetryConfig(count=2, interval=5.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    with pytest.raises(_TransientError, match="fail-3"):
        asyncio.run(retry.execute(_always_fail))

    # Assert
    assert call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(5.0)


def test_execute_raises_non_transient_immediately(mocker: Any) -> None:
    """一時的でない例外はリトライされず即座に送出されること.

    Arrange:
        一時的でないエラーを発生させる関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        _NonTransientErrorが即座に送出されること。
        関数が1回だけ呼び出されること。
        asyncio.sleepが呼び出されないこと。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _raise_non_transient() -> None:
        nonlocal call_count
        call_count += 1
        raise _NonTransientError("fatal")

    retry = AsyncRetryable(
        config=RetryConfig(count=3, interval=5.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    with pytest.raises(_NonTransientError, match="fatal"):
        asyncio.run(retry.execute(_raise_non_transient))

    # Assert
    assert call_count == 1
    mock_sleep.assert_not_called()


def test_execute_with_zero_count_no_retry(mocker: Any) -> None:
    """count=0の場合、リトライされず初回失敗がそのまま送出されること.

    Arrange:
        count=0のRetryConfigを用意する。
        常に一時的エラーを発生させる関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        _TransientErrorが送出されること。
        関数が1回だけ呼び出されること。
        asyncio.sleepが呼び出されないこと。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _fail() -> None:
        nonlocal call_count
        call_count += 1
        raise _TransientError("no retry")

    retry = AsyncRetryable(
        config=RetryConfig(count=0, interval=1.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    with pytest.raises(_TransientError, match="no retry"):
        asyncio.run(retry.execute(_fail))

    # Assert
    assert call_count == 1
    mock_sleep.assert_not_called()


def test_execute_with_empty_transient_exceptions_raises_immediately(
    mocker: Any,
) -> None:
    """transient_exceptions=()の場合、例外が捕捉されず即座に送出されること.

    Arrange:
        transient_exceptions=()のAsyncRetryableを用意する。
        エラーを発生させる関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        例外がそのまま送出されること。
        asyncio.sleepが呼び出されないこと。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _fail() -> None:
        nonlocal call_count
        call_count += 1
        raise _TransientError("uncaught")

    retry = AsyncRetryable(
        config=RetryConfig(count=3, interval=5.0),
        transient_exceptions=(),
    )

    # Act
    with pytest.raises(_TransientError, match="uncaught"):
        asyncio.run(retry.execute(_fail))

    # Assert
    assert call_count == 1
    mock_sleep.assert_not_called()


def test_execute_sleeps_between_retries(mocker: Any) -> None:
    """リトライ間でasyncio.sleepが呼び出されること.

    Arrange:
        sleepをパッチする。
        1回目は失敗、2回目は成功する関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        asyncio.sleepがintervalの値で1回呼び出されること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")

    call_count = 0

    async def _flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _TransientError("retry me")
        return "done"

    retry = AsyncRetryable(
        config=RetryConfig(count=2, interval=5.0),
        transient_exceptions=(_TransientError,),
    )

    # Act
    result = asyncio.run(retry.execute(_flaky))

    # Assert
    assert result == "done"
    mock_sleep.assert_called_once_with(5.0)


def test_execute_skips_retry_when_predicate_returns_false(
    mocker: Any,
) -> None:
    """should_retry_exceptionがFalseを返した場合、リトライされず即座に送出されること.

    Arrange:
        should_retry_exceptionを指定する。
        一時的エラーを発生させる関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        例外が即座に送出されること。
        関数が1回だけ呼び出されること。
        asyncio.sleepが呼び出されないこと。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _fail() -> None:
        nonlocal call_count
        call_count += 1
        raise _TransientError("skip me")

    retry = AsyncRetryable(
        config=RetryConfig(count=3, interval=5.0),
        transient_exceptions=(_TransientError,),
        should_retry_exception=lambda _: False,
    )

    # Act
    with pytest.raises(_TransientError, match="skip me"):
        asyncio.run(retry.execute(_fail))

    # Assert
    assert call_count == 1
    mock_sleep.assert_not_called()


def test_execute_retries_when_predicate_returns_true(
    mocker: Any,
) -> None:
    """should_retry_exceptionがTrueを返した場合、リトライされること.

    Arrange:
        should_retry_exceptionを指定する。
        1回目は失敗、2回目は成功する関数を用意する。

    Act:
        execute()を実行する。

    Assert:
        結果が返されること。
        関数が2回呼び出されること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    async def _flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _TransientError("retry me")
        return "ok"

    retry = AsyncRetryable(
        config=RetryConfig(count=2, interval=5.0),
        transient_exceptions=(_TransientError,),
        should_retry_exception=lambda _: True,
    )

    # Act
    result = asyncio.run(retry.execute(_flaky))

    # Assert
    assert result == "ok"
    assert call_count == 2
    mock_sleep.assert_called_once_with(5.0)
