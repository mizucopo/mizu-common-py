"""Discord Webhook通知クライアントモジュール.

Discord Webhookを使用したメッセージ送信機能を提供する。
"""

from typing import Any

import requests

from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed


class DiscordClient:
    """Discord Webhook通知クライアント.

    Webhook URLを使用してDiscordチャンネルにメッセージを送信する。
    """

    def __init__(self, webhook_url: str) -> None:
        """クライアントを初期化する.

        Args:
            webhook_url: Discord Webhook URL
        """
        self._webhook_url = webhook_url

    def send_message(
        self,
        content: str,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """テキストメッセージを送信する.

        Args:
            content: 送信するメッセージ内容
            username: オーバーライドするユーザー名
            avatar_url: オーバーライドするアバターURL

        Raises:
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        payload: dict[str, Any] = {"content": content}
        if username is not None:
            payload["username"] = username
        if avatar_url is not None:
            payload["avatar_url"] = avatar_url

        self._send_request(payload)

    def send_embed(
        self,
        embed: DiscordEmbed,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """Embedメッセージを送信する.

        Args:
            embed: 送信するEmbed
            username: オーバーライドするユーザー名
            avatar_url: オーバーライドするアバターURL

        Raises:
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        payload: dict[str, Any] = {"embeds": [embed.to_dict()]}
        if username is not None:
            payload["username"] = username
        if avatar_url is not None:
            payload["avatar_url"] = avatar_url

        self._send_request(payload)

    def send_embeds(
        self,
        embeds: list[DiscordEmbed],
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """複数のEmbedメッセージを送信する.

        Args:
            embeds: 送信するEmbedのリスト（最大10件）
            username: オーバーライドするユーザー名
            avatar_url: オーバーライドするアバターURL

        Raises:
            ValueError: Embed数が10を超える場合
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        if len(embeds) > 10:
            raise ValueError("Embed数は最大10件までです")

        payload: dict[str, Any] = {"embeds": [e.to_dict() for e in embeds]}
        if username is not None:
            payload["username"] = username
        if avatar_url is not None:
            payload["avatar_url"] = avatar_url

        self._send_request(payload)

    def _send_request(self, payload: dict[str, Any]) -> None:
        """Webhookリクエストを送信する.

        Args:
            payload: 送信するペイロード

        Raises:
            DiscordWebhookError: リクエストが失敗した場合
        """
        response = requests.post(
            self._webhook_url,
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 204):
            raise DiscordWebhookError(
                f"Discord通知の送信に失敗しました: status={response.status_code}, "
                f"response={response.text}"
            )
