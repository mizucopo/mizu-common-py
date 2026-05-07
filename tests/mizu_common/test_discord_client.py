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


def _make_long_message(lines: int, line_length: int = 50) -> str:
    """指定行数・行長のメッセージを生成する."""
    line = "a" * line_length
    return "\n".join([line] * lines)


def test_send_message_sends_long_message_in_multiple_chunks(
    mocker: Any,
) -> None:
    """2000文字を超えるメッセージが複数チャンクに分割送信されること.

    Arrange:
        2000文字を超えるメッセージを用意する。
        成功レスポンスを設定する。

    Act:
        send_message()を実行する。

    Assert:
        複数回POSTされること。
        全チャンクが2000文字以下であること。
        チャンクを改行で結合すると元のメッセージに戻ること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    client.send_message(message)

    # Assert
    assert transport.request_count > 1
    chunks: list[str] = []
    for req in transport.requests:
        assert req.json is not None
        content = req.json["content"]
        assert isinstance(content, str)
        chunks.append(content)
    for chunk in chunks:
        assert len(chunk) <= DiscordClient.MAX_MESSAGE_LENGTH
    assert "\n".join(chunks) == message


def test_send_message_sends_message_at_max_length_as_single_request(
    mocker: Any,
) -> None:
    """2000文字ちょうどのメッセージが1回のPOSTで送信されること.

    Arrange:
        2000文字ちょうどのメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        1回だけPOSTされること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    message = "a" * 2000

    # Act
    client.send_message(message)

    # Assert
    assert transport.request_count == 1


def test_send_message_truncates_long_line(mocker: Any) -> None:
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
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    long_line = "a" * 3000

    # Act
    client.send_message(long_line)

    # Assert
    assert transport.request_count == 1
    payload = transport.last_request.json
    assert payload is not None
    content = payload["content"]
    assert isinstance(content, str)
    assert len(content) <= DiscordClient.MAX_MESSAGE_LENGTH
    assert "... (切り捨てられました)" in content


def test_send_message_inherits_username_and_avatar_across_chunks(
    mocker: Any,
) -> None:
    """分割送信時にusernameとavatar_urlが全チャンクに含まれること.

    Arrange:
        2000文字を超えるメッセージを用意する。

    Act:
        usernameとavatar_urlを指定してsend_message()を実行する。

    Assert:
        全POSTのペイロードにusernameとavatar_urlが含まれること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    client.send_message(
        message,
        username="Bot",
        avatar_url="https://example.com/img.png",
    )

    # Assert
    for req in transport.requests:
        payload = req.json
        assert payload is not None
        assert payload["username"] == "Bot"
        assert payload["avatar_url"] == "https://example.com/img.png"


def test_send_message_raises_error_during_split_send(
    mocker: Any,
) -> None:
    """分割送信中にPOSTが失敗した場合にDiscordWebhookErrorが発生されること.

    Arrange:
        2000文字を超えるメッセージを用意する。
        1回目は成功、2回目は失敗するレスポンスを設定する。

    Act:
        send_message()を実行する。

    Assert:
        DiscordWebhookErrorが送出されること。
        1回目のPOSTは成功していること。
    """
    # Arrange
    transport = FakeHttpTransport(responses=[(204, ""), (500, "Server Error")])
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    message = _make_long_message(lines=100, line_length=50)

    # Act
    with pytest.raises(DiscordWebhookError, match="Discord通知の送信に失敗しました"):
        client.send_message(message)

    # Assert
    assert transport.request_count >= 2


def test_send_message_does_not_send_empty_chunk_for_trailing_newline(
    mocker: Any,
) -> None:
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
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)
    message = ("a" * 2000) + "\n"

    # Act
    client.send_message(message)

    # Assert
    assert transport.request_count == 1
    payload = transport.last_request.json
    assert payload is not None
    content = payload["content"]
    assert isinstance(content, str)
    assert content != ""
    assert len(content) <= DiscordClient.MAX_MESSAGE_LENGTH


def test_send_message_empty_string_sends_single_request(
    mocker: Any,
) -> None:
    """空文字列のメッセージが1回のPOSTで送信されること.

    Arrange:
        空文字列のメッセージを用意する。

    Act:
        send_message()を実行する。

    Assert:
        1回だけPOSTされること。
    """
    # Arrange
    transport = FakeHttpTransport()
    mocker.patch("mizu_common.discord_client.requests.post", transport.post)
    client = DiscordClient(TEST_WEBHOOK_URL)

    # Act
    client.send_message("")

    # Assert
    assert transport.request_count == 1
    assert transport.last_request.json == {"content": ""}
