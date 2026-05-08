"""Discord Webhook通知クライアントのテスト."""

import json

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
    def handler(request: httpx.Request) -> httpx.Response:
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
