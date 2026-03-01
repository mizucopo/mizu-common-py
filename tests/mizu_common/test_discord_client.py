"""Discord Webhook通知クライアントのテスト."""

from typing import Any
from unittest.mock import Mock

import pytest

from mizu_common.discord_client import DiscordClient
from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed


def test_send_message_sends_text_message_successfully(mocker: Any) -> None:
    """send_messageがテキストメッセージを正常に送信すること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスをモックする。

    Act:
        send_message()を実行する。

    Assert:
        メッセージが送信されること。
        ペイロードに正しい内容が含まれること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post = mocker.patch(
        "mizu_common.discord_client.requests.post", return_value=mock_response
    )

    client = DiscordClient("https://discord.com/api/webhooks/123/abc")

    # Act
    client.send_message("Hello, Discord!")

    # Assert
    mock_post.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc",
        json={"content": "Hello, Discord!"},
        timeout=30,
    )


def test_send_message_with_username_and_avatar(mocker: Any) -> None:
    """send_messageがユーザー名とアバターを含めて送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスをモックする。

    Act:
        ユーザー名とアバターURLを指定してsend_message()を実行する。

    Assert:
        ペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post = mocker.patch(
        "mizu_common.discord_client.requests.post", return_value=mock_response
    )
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")

    # Act
    client.send_message(
        "Hello!",
        username="Bot",
        avatar_url="https://example.com/avatar.png",
    )

    # Assert
    mock_post.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc",
        json={
            "content": "Hello!",
            "username": "Bot",
            "avatar_url": "https://example.com/avatar.png",
        },
        timeout=30,
    )


def test_send_message_raises_error_on_failure(mocker: Any) -> None:
    """send_messageが失敗時にRuntimeErrorが発生すること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        send_message()を実行する。

    Assert:
        RuntimeErrorが発生すること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Unknown Webhook"
    mocker.patch("mizu_common.discord_client.requests.post", return_value=mock_response)
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")

    # Act & Assert
    with pytest.raises(DiscordWebhookError, match="Discord通知の送信に失敗しました"):
        client.send_message("Hello!")


def test_send_embed_sends_embed_message_successfully(mocker: Any) -> None:
    """send_embedがEmbedメッセージを正常に送信すること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスをモックする。
        Embedを用意する。

    Act:
        send_embed()を実行する。

    Assert:
        メッセージが送信されること。
        ペイロードにembedsが含まれること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post = mocker.patch(
        "mizu_common.discord_client.requests.post", return_value=mock_response
    )
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")
    embed = DiscordEmbed(
        title="Test Title",
        description="Test Description",
        color=0x3498DB,
        url="https://example.com",
    )

    # Act
    client.send_embed(embed)

    # Assert
    mock_post.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc",
        json={
            "embeds": [
                {
                    "title": "Test Title",
                    "description": "Test Description",
                    "color": 0x3498DB,
                    "url": "https://example.com",
                }
            ]
        },
        timeout=30,
    )


def test_send_embeds_with_multiple_embeds(mocker: Any) -> None:
    """send_embedsが複数のEmbedを送信できること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスをモックする。
        複数のEmbedを用意する。

    Act:
        複数のEmbedを指定してsend_embeds()を実行する。

    Assert:
        ペイロードに複数のembedsが含まれること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post = mocker.patch(
        "mizu_common.discord_client.requests.post", return_value=mock_response
    )
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")
    embeds = [
        DiscordEmbed(title="First"),
        DiscordEmbed(title="Second"),
    ]
    # Act
    client.send_embeds(embeds)

    # Assert
    call_args = mock_post.call_args
    assert len(call_args[1]["json"]["embeds"]) == 2


def test_send_embeds_raises_error_when_exceeds_limit() -> None:
    """send_embedsがEmbed数11以上でValueErrorを発生すること.

    Arrange:
        11個のEmbedを用意する。

    Act & Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")
    embeds = [DiscordEmbed(title=f"Title {i}") for i in range(11)]

    # Act & Assert
    with pytest.raises(ValueError, match="Embed数は最大10件までです"):
        client.send_embeds(embeds)


def test_send_embed_with_username_and_avatar(mocker: Any) -> None:
    """send_embedがユーザー名とアバターを含めて送信されること.

    Arrange:
        Webhook URLを用意する。
        成功レスポンスをモックする。
        Embed、ユーザー名、アバターURLを用意する。

    Act:
        send_embed()を実行する。

    Assert:
        ペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post = mocker.patch(
        "mizu_common.discord_client.requests.post", return_value=mock_response
    )
    client = DiscordClient("https://discord.com/api/webhooks/123/abc")
    embed = DiscordEmbed(title="Test")

    # Act
    client.send_embed(
        embed,
        username="Bot",
        avatar_url="https://example.com/avatar.png",
    )

    # Assert
    call_args = mock_post.call_args
    assert call_args[1]["json"]["username"] == "Bot"
    assert call_args[1]["json"]["avatar_url"] == "https://example.com/avatar.png"
