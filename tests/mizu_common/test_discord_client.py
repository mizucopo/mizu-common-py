"""Discord Webhook通知クライアントのテスト."""

import json
import logging
from typing import Any

import httpx
import pytest

from mizu_common.discord_client import DiscordClient
from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed
from mizu_common.retry_config import RetryConfig

TEST_WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"

pytestmark = pytest.mark.asyncio


async def test_send_message_sends_text_message_successfully() -> None:
    """send_messageでテキストメッセージが正常に送信されること.

    Arrange:
        MockTransportを設定する。
        成功レスポンスを返す。

    Act:
        send_message()を実行する。

    Assert:
        リクエストが送信されること。
        ペイロードに正しい内容が含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message("Hello, Discord!")

    # Assert
    assert len(captured) == 1
    assert str(captured[0].url) == TEST_WEBHOOK_URL
    body = json.loads(captured[0].content)
    assert body == {"content": "Hello, Discord!"}


async def test_send_message_with_username_and_avatar() -> None:
    """send_messageでユーザー名とアバターが含めて送信されること.

    Arrange:
        MockTransportを設定する。
        成功レスポンスを返す。

    Act:
        ユーザー名とアバターURLを指定してsend_message()を実行する。

    Assert:
        ペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(
            "Hello!",
            username="Bot",
            avatar_url="https://example.com/avatar.png",
        )

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body == {
        "content": "Hello!",
        "username": "Bot",
        "avatar_url": "https://example.com/avatar.png",
    }


async def test_send_message_raises_error_on_failure() -> None:
    """send_messageの失敗時にDiscordWebhookErrorが発生されること.

    Arrange:
        404エラーレスポンスを返すMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが発生すること。
        status_codeに404が設定されること。
    """

    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, text="Unknown Webhook")

    transport = httpx.MockTransport(handler)

    # Act & Assert
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        with pytest.raises(
            DiscordWebhookError,
            match="Discord通知の送信に失敗しました",
        ) as exc_info:
            await client.send_message("Hello!")
    assert exc_info.value.status_code == 404


async def test_send_message_raises_runtime_error_outside_context() -> None:
    """async withブロック外でsend_messageを呼び出した場合にRuntimeErrorが発生すること.

    Arrange:
        DiscordClientを生成する（async withに入らない）。

    Act & Assert:
        send_message()を実行するとRuntimeErrorが発生すること。
    """
    # Arrange
    client = DiscordClient(TEST_WEBHOOK_URL)

    # Act & Assert
    with pytest.raises(RuntimeError, match="async with"):
        await client.send_message("Hello!")


def _make_long_message(lines: int, line_length: int = 50) -> str:
    """指定行数・行長のメッセージを生成する."""
    line = "a" * line_length
    return "\n".join([line] * lines)


# --- Task 5: チャンク分割テスト ---


async def test_send_message_sends_long_message_in_multiple_chunks() -> None:
    """2000文字を超えるメッセージが複数チャンクに分割送信されること.

    Arrange:
        2000文字を超えるメッセージを用意する。
        成功レスポンスを返すMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        複数回POSTされること。
        全チャンクが2000文字以下であること。
        チャンクを改行で結合すると元のメッセージに戻ること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(message)

    # Assert
    assert len(captured) > 1
    chunks: list[str] = []
    for req in captured:
        body = json.loads(req.content)
        content = body["content"]
        assert isinstance(content, str)
        chunks.append(content)
    for chunk in chunks:
        assert len(chunk) <= DiscordClient.MAX_MESSAGE_LENGTH
    assert "\n".join(chunks) == message


async def test_send_message_sends_message_at_max_length_as_single_request() -> None:
    """2000文字ちょうどのメッセージが1回のPOSTで送信されること.

    Arrange:
        2000文字ちょうどのメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        1回だけPOSTされること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = "a" * 2000

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(message)

    # Assert
    assert len(captured) == 1


async def test_send_message_truncates_long_line() -> None:
    """1行が2000文字を超える場合に切り捨てられること.

    Arrange:
        2000文字を超える1行を含むメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        送信されるチャンクの長さが2000文字以下であること。
        チャンクに切り捨て通知が含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    long_line = "a" * 3000

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(long_line)

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    content = body["content"]
    assert isinstance(content, str)
    assert len(content) <= DiscordClient.MAX_MESSAGE_LENGTH
    assert "... (切り捨てられました)" in content


async def test_send_message_inherits_username_and_avatar_across_chunks() -> None:
    """分割送信時にusernameとavatar_urlが全チャンクに含まれること.

    Arrange:
        2000文字を超えるメッセージを用意する。

    Act:
        usernameとavatar_urlを指定してsend_message()を実行する。

    Assert:
        全POSTのペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(
            message,
            username="Bot",
            avatar_url="https://example.com/img.png",
        )

    # Assert
    for req in captured:
        body = json.loads(req.content)
        assert body["username"] == "Bot"
        assert body["avatar_url"] == "https://example.com/img.png"


async def test_send_message_raises_error_during_split_send() -> None:
    """分割送信中にPOSTが失敗した場合にDiscordWebhookErrorが発生されること.

    Arrange:
        2000文字を超えるメッセージを用意する。
        1回目は成功、2回目は失敗するレスポンスを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが送出されること。
        status_codeに500が設定されること。
    """
    # Arrange
    responses = [
        httpx.Response(204),
        httpx.Response(500, text="Server Error"),
    ]
    iter_responses = iter(responses)

    def handler(_request: httpx.Request) -> httpx.Response:
        return next(iter_responses)

    transport = httpx.MockTransport(handler)
    message = _make_long_message(lines=100, line_length=50)

    # Act & Assert
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        with pytest.raises(
            DiscordWebhookError,
            match="Discord通知の送信に失敗しました",
        ) as exc_info:
            await client.send_message(message)
    assert exc_info.value.status_code == 500


async def test_send_message_does_not_send_empty_chunk_for_trailing_newline() -> None:
    """末尾改行だけの空チャンクが送信されないこと.

    Arrange:
        2000文字ちょうどの行と末尾改行を含むメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        空文字列チャンクが送信されないこと。
        送信チャンクが2000文字以下であること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = ("a" * 2000) + "\n"

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(message)

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    content = body["content"]
    assert isinstance(content, str)
    assert content != ""
    assert len(content) <= DiscordClient.MAX_MESSAGE_LENGTH


async def test_send_message_empty_string_sends_single_request() -> None:
    """空文字列のメッセージが1回のPOSTで送信されること.

    Arrange:
        空文字列のメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        1回だけPOSTされること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message("")

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body == {"content": ""}


async def test_send_message_sends_newline_only_long_message_in_chunks() -> None:
    """改行のみの2000文字超メッセージが分割送信されること.

    Arrange:
        改行のみで2000文字を超えるメッセージを用意する。
        成功レスポンスを返すMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        1回以上POSTされること。
        全チャンクが2000文字以下であること。
        空文字列チャンクが含まれないこと。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = "\n" * 2001

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_message(message)

    # Assert
    assert len(captured) >= 1
    for req in captured:
        body = json.loads(req.content)
        content = body["content"]
        assert isinstance(content, str)
        assert content != ""
        assert len(content) <= DiscordClient.MAX_MESSAGE_LENGTH


# --- Task 6: send_embed / send_embeds テスト ---


async def test_send_embed_sends_embed_message_successfully() -> None:
    """send_embedでEmbedメッセージが正常に送信されること.

    Arrange:
        MockTransportを設定する。
        成功レスポンスを返す。
        Embedを用意する。

    Act:
        send_embed()を実行する。

    Assert:
        メッセージが送信されること。
        ペイロードにembedsが含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    embed = DiscordEmbed(
        title="Test Title",
        description="Test Description",
        color=0x3498DB,
        url="https://example.com",
    )

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_embed(embed)

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body == {
        "embeds": [
            {
                "title": "Test Title",
                "description": "Test Description",
                "color": 0x3498DB,
                "url": "https://example.com",
            }
        ]
    }


async def test_send_embeds_with_multiple_embeds() -> None:
    """send_embedsで複数のEmbedが送信されること.

    Arrange:
        MockTransportを設定する。
        複数のEmbedを用意する。

    Act:
        複数のEmbedを指定してsend_embeds()を実行する。

    Assert:
        ペイロードに複数のembedsが含まれること。
    """
    # Arrange
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    embeds = [
        DiscordEmbed(title="First"),
        DiscordEmbed(title="Second"),
    ]

    # Act
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        await client.send_embeds(embeds)

    # Assert
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert len(body["embeds"]) == 2


async def test_send_embeds_raises_error_when_exceeds_limit() -> None:
    """send_embedsでEmbed数11以上の場合にValueErrorが発生されること.

    Arrange:
        11個のEmbedを用意する。

    Act & Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    client = DiscordClient(TEST_WEBHOOK_URL)
    embeds = [DiscordEmbed(title=f"Title {i}") for i in range(11)]

    # Act & Assert
    with pytest.raises(ValueError, match="Embed数は最大10件までです"):
        await client.send_embeds(embeds)


# --- Task 7: エラーハンドリングテスト ---


async def test_send_message_converts_connect_error_to_discord_webhook_error() -> None:
    """httpx.ConnectErrorがDiscordWebhookErrorに変換されること.

    Arrange:
        ConnectErrorを発生させるMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが発生すること。
        status_codeがNoneであること。
    """

    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)

    # Act & Assert
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        with pytest.raises(
            DiscordWebhookError,
            match="Discord通知の送信に失敗しました",
        ) as exc_info:
            await client.send_message("Hello!")
    assert exc_info.value.status_code is None


async def test_send_message_converts_timeout_error_to_discord_webhook_error() -> None:
    """httpx.TimeoutExceptionがDiscordWebhookErrorに変換されること.

    Arrange:
        TimeoutExceptionを発生させるMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが発生すること。
        status_codeがNoneであること。
    """

    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Request timed out")

    transport = httpx.MockTransport(handler)

    # Act & Assert
    async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
        with pytest.raises(
            DiscordWebhookError,
            match="Discord通知の送信に失敗しました",
        ) as exc_info:
            await client.send_message("Hello!")
    assert exc_info.value.status_code is None


# --- Task 8: リトライテスト ---


async def test_send_message_retries_on_5xx_error(mocker: Any) -> None:
    """5xxエラー時にリトライされること.

    Arrange:
        1回目は500エラー、2回目は成功するMockTransportを設定する。
        retry_configを指定する。
        asyncio.sleepをモックする。

    Act:
        send_message()を実行する。

    Assert:
        最終的に成功すること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(status_code=500, text="Server Error")
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    retry_config = RetryConfig(count=2, interval=1.0)

    # Act
    async with DiscordClient(
        TEST_WEBHOOK_URL, transport=transport, retry_config=retry_config
    ) as client:
        await client.send_message("Hello!")

    # Assert
    assert call_count == 2
    mock_sleep.assert_called_once_with(1.0)


async def test_send_message_does_not_retry_on_4xx_error() -> None:
    """4xxエラー時はリトライされず即座にDiscordWebhookErrorが送出されること.

    Arrange:
        404エラーを返すMockTransportを設定する。
        retry_configを指定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが即座に送出されること。
        status_codeに404が設定されること。
    """
    # Arrange
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=404, text="Unknown Webhook")

    transport = httpx.MockTransport(handler)
    retry_config = RetryConfig(count=3, interval=1.0)

    # Act & Assert
    async with DiscordClient(
        TEST_WEBHOOK_URL, transport=transport, retry_config=retry_config
    ) as client:
        with pytest.raises(DiscordWebhookError) as exc_info:
            await client.send_message("Hello!")
    assert exc_info.value.status_code == 404
    assert call_count == 1


async def test_send_message_retries_on_connect_error(mocker: Any) -> None:
    """接続エラー時にリトライされること.

    Arrange:
        1回目はConnectError、2回目は成功するMockTransportを設定する。
        retry_configを指定する。
        asyncio.sleepをモックする。

    Act:
        send_message()を実行する。

    Assert:
        最終的に成功すること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    retry_config = RetryConfig(count=2, interval=1.0)

    # Act
    async with DiscordClient(
        TEST_WEBHOOK_URL, transport=transport, retry_config=retry_config
    ) as client:
        await client.send_message("Hello!")

    # Assert
    assert call_count == 2
    mock_sleep.assert_called_once_with(1.0)


async def test_send_message_raises_after_all_retries_exhausted(
    mocker: Any,
) -> None:
    """全リトライ失敗後にDiscordWebhookErrorが送出されること.

    Arrange:
        常に500エラーを返すMockTransportを設定する。
        retry_config（count=2）を指定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが送出されること。
        status_codeに500が設定されること。
    """
    # Arrange
    mock_sleep = mocker.patch("mizu_common.async_retryable.asyncio.sleep")
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=500, text="Server Error")

    transport = httpx.MockTransport(handler)
    retry_config = RetryConfig(count=2, interval=1.0)

    # Act & Assert
    async with DiscordClient(
        TEST_WEBHOOK_URL, transport=transport, retry_config=retry_config
    ) as client:
        with pytest.raises(
            DiscordWebhookError,
            match="Discord通知の送信に失敗しました",
        ) as exc_info:
            await client.send_message("Hello!")
    assert exc_info.value.status_code == 500
    assert call_count == 3  # 初回 + 2リトライ
    assert mock_sleep.call_count == 2


# --- Task 9: ログテスト ---


async def test_send_message_logs_chunk_progress(caplog: Any) -> None:
    """チャンク分割送信時にINFOログが出力されること.

    Arrange:
        2000文字を超えるメッセージを用意する。
        成功レスポンスを返すMockTransportを設定する。

    Act:
        send_message()を実行する。

    Assert:
        チャンク送信開始・完了のログがINFOレベルで出力されること。
    """

    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=204)

    transport = httpx.MockTransport(handler)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    with caplog.at_level(logging.INFO, logger="mizu_common.discord_client"):
        async with DiscordClient(TEST_WEBHOOK_URL, transport=transport) as client:
            await client.send_message(message)

    # Assert
    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("チャンク 1/" in msg and "送信開始" in msg for msg in info_messages)
    assert any("チャンク 1/" in msg and "送信完了" in msg for msg in info_messages)
    assert any("チャンク 2/" in msg and "送信開始" in msg for msg in info_messages)
    assert any("チャンク 2/" in msg and "送信完了" in msg for msg in info_messages)
