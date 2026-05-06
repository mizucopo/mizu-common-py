"""Discord Webhook通知クライアントのテスト."""

from typing import Any

import pytest

from mizu_common.discord_client import DiscordClient
from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed
from tests.fakes.fake_http_transport import FakeHttpTransport

TEST_WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"


def test_send_message_sends_text_message_successfully(
    mocker: Any,
) -> None:
    """send_messageでテキストメッセージが正常に送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスを設定する。

    Act:
        send_message()を実行する。

    Assert:
        メッセージが送信されること。
        ペイロードに正しい内容が含まれること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)

    # Act
    client.send_message("Hello, Discord!")

    # Assert
    assert transport.request_count == 1
    assert transport.last_request.url == TEST_WEBHOOK_URL
    assert transport.last_request.json == {"content": "Hello, Discord!"}


def test_send_message_with_username_and_avatar(
    mocker: Any,
) -> None:
    """send_messageでユーザー名とアバターが含めて送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスを設定する。

    Act:
        ユーザー名とアバターURLを指定してsend_message()を実行する。

    Assert:
        ペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)

    # Act
    client.send_message(
        "Hello!",
        username="Bot",
        avatar_url="https://example.com/avatar.png",
    )

    # Assert
    assert transport.request_count == 1
    assert transport.last_request.json == {
        "content": "Hello!",
        "username": "Bot",
        "avatar_url": "https://example.com/avatar.png",
    }


def test_send_message_raises_error_on_failure(
    mocker: Any,
) -> None:
    """send_messageの失敗時にDiscordWebhookErrorが発生されること.

    Arrange:
        エラーレスポンスを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが発生すること。
    """
    # Arrange
    transport = FakeHttpTransport(status_code=404, text="Unknown Webhook")
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)

    # Act & Assert
    with pytest.raises(DiscordWebhookError, match="Discord通知の送信に失敗しました"):
        client.send_message("Hello!")


def test_send_embed_sends_embed_message_successfully(
    mocker: Any,
) -> None:
    """send_embedでEmbedメッセージが正常に送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスを設定する。
        Embedを用意する。

    Act:
        send_embed()を実行する。

    Assert:
        メッセージが送信されること。
        ペイロードにembedsが含まれること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    embed = DiscordEmbed(
        title="Test Title",
        description="Test Description",
        color=0x3498DB,
        url="https://example.com",
    )

    # Act
    client.send_embed(embed)

    # Assert
    assert transport.request_count == 1
    assert transport.last_request.json == {
        "embeds": [
            {
                "title": "Test Title",
                "description": "Test Description",
                "color": 0x3498DB,
                "url": "https://example.com",
            }
        ]
    }


def test_send_embeds_with_multiple_embeds(
    mocker: Any,
) -> None:
    """send_embedsで複数のEmbedが送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスを設定する。
        複数のEmbedを用意する。

    Act:
        複数のEmbedを指定してsend_embeds()を実行する。

    Assert:
        ペイロードに複数のembedsが含まれること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    embeds = [
        DiscordEmbed(title="First"),
        DiscordEmbed(title="Second"),
    ]

    # Act
    client.send_embeds(embeds)

    # Assert
    assert transport.request_count == 1
    assert len(transport.last_request.json["embeds"]) == 2  # type: ignore[arg-type, index]


def test_send_embeds_raises_error_when_exceeds_limit() -> None:
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
        client.send_embeds(embeds)
