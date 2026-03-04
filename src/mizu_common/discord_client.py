"""Discord Webhook通知クライアントモジュール.

Discord Webhookを使用したメッセージ送信機能を提供する。
"""

from typing import Any

import requests

from mizu_common.constants.http_timeout import DEFAULT_TIMEOUT
from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed


class DiscordClient:
    """Discord Webhook通知クライアント.

    Webhook URLを使用してDiscordチャンネルにメッセージを送信する。
    """

    MAX_EMBEDS = 10

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
        payload = self._build_payload({"content": content}, username, avatar_url)
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
        payload = self._build_payload(
            {"embeds": [embed.to_dict()]}, username, avatar_url
        )
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
        if len(embeds) > self.MAX_EMBEDS:
            raise ValueError(f"Embed数は最大{self.MAX_EMBEDS}件までです")

        payload = self._build_payload(
            {"embeds": [e.to_dict() for e in embeds]}, username, avatar_url
        )
        self._send_request(payload)

    def _build_payload(
        self,
        base_payload: dict[str, Any],
        username: str | None,
        avatar_url: str | None,
    ) -> dict[str, Any]:
        """Webhookペイロードを構築する.

        Args:
            base_payload: 基本ペイロード（contentまたはembeds）
            username: オーバーライドするユーザー名
            avatar_url: オーバーライドするアバターURL

        Returns:
            完成したペイロード
        """
        if username is not None:
            base_payload["username"] = username
        if avatar_url is not None:
            base_payload["avatar_url"] = avatar_url
        return base_payload

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
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code not in (200, 204):
            raise DiscordWebhookError(
                f"Discord通知の送信に失敗しました: status={response.status_code}, "
                f"response={response.text}"
            )
