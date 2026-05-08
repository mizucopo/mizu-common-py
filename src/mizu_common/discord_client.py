"""Discord Webhook通知クライアントモジュール.

Discord Webhookを使用したメッセージ送信機能を提供する。
"""

import logging
from types import TracebackType
from typing import Any, Self

import httpx

from mizu_common.async_retryable import AsyncRetryable
from mizu_common.constants.http_timeout import DEFAULT_TIMEOUT
from mizu_common.exceptions.discord_webhook_error import DiscordWebhookError
from mizu_common.models.discord_embed import DiscordEmbed
from mizu_common.retry_config import RetryConfig

logger = logging.getLogger(__name__)


class DiscordClient:
    """Discord Webhook通知クライアント.

    Webhook URLを使用してDiscordチャンネルにメッセージを送信する。
    """

    MAX_EMBEDS = 10
    MAX_MESSAGE_LENGTH = 2000

    def __init__(
        self,
        webhook_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        retry_config: RetryConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """クライアントを初期化する.

        Args:
            webhook_url: Discord Webhook URL
            timeout: リクエストタイムアウト（秒）
            retry_config: リトライ設定（Noneの場合はリトライなし）
            transport: テスト用のカスタムTransport
        """
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._transport = transport
        self._retryable = (
            AsyncRetryable(
                config=retry_config,
                transient_exceptions=(DiscordWebhookError,),
                should_retry_exception=self._should_retry_exception,
            )
            if retry_config
            else None
        )
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_message(
        self,
        content: str,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """テキストメッセージを送信する.

        2000文字を超える場合は自動的に分割して複数回送信する。

        Args:
            content: 送信するメッセージ内容
            username: オーバーライドするユーザー名
            avatar_url: オーバーライドするアバターURL

        Raises:
            RuntimeError: async withブロック外で呼び出された場合
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        chunks = self._split_message(content)
        total = len(chunks)
        for i, chunk in enumerate(chunks, start=1):
            if total > 1:
                logger.info("チャンク %d/%d 送信開始", i, total)
            payload = self._build_payload({"content": chunk}, username, avatar_url)
            await self._send_request_with_retry(payload)
            if total > 1:
                logger.info("チャンク %d/%d 送信完了", i, total)

    async def send_embed(
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
            RuntimeError: async withブロック外で呼び出された場合
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        payload = self._build_payload(
            {"embeds": [embed.to_dict()]}, username, avatar_url
        )
        await self._send_request_with_retry(payload)

    async def send_embeds(
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
            RuntimeError: async withブロック外で呼び出された場合
            DiscordWebhookError: メッセージの送信に失敗した場合
        """
        if len(embeds) > self.MAX_EMBEDS:
            raise ValueError(f"Embed数は最大{self.MAX_EMBEDS}件までです")

        payload = self._build_payload(
            {"embeds": [e.to_dict() for e in embeds]}, username, avatar_url
        )
        await self._send_request_with_retry(payload)

    def _require_client(self) -> httpx.AsyncClient:
        """context manager 開始済みのAsyncClientを取得する.

        Raises:
            RuntimeError: async withブロック外で呼び出された場合
        """
        if self._client is None:
            raise RuntimeError("DiscordClientはasync withブロック内で使用してください")
        return self._client

    async def _send_request(self, payload: dict[str, Any]) -> None:
        """Webhookリクエストを送信し、例外を正規化する.

        Args:
            payload: 送信するペイロード

        Raises:
            DiscordWebhookError: リクエストが失敗した場合
        """
        client = self._require_client()
        try:
            response = await client.post(
                self._webhook_url,
                json=payload,
            )
        except httpx.RequestError as e:
            raise DiscordWebhookError(
                f"Discord通知の送信に失敗しました: {e}",
                status_code=None,
            ) from e

        if response.status_code not in (200, 204):
            raise DiscordWebhookError(
                "Discord通知の送信に失敗しました: "
                f"status={response.status_code}, "
                f"response={response.text}",
                status_code=response.status_code,
            )

    async def _send_request_with_retry(self, payload: dict[str, Any]) -> None:
        """リトライ設定に応じてリクエストを送信する."""
        if self._retryable:
            await self._retryable.execute(lambda: self._send_request(payload))
        else:
            await self._send_request(payload)

    @staticmethod
    def _should_retry_exception(error: Exception) -> bool:
        """HTTPステータスに基づきリトライ可否を判定する."""
        assert isinstance(error, DiscordWebhookError)
        if error.status_code is None:
            return True
        return error.status_code == 429 or error.status_code >= 500

    def _split_message(self, content: str) -> list[str]:
        """メッセージをDiscordの文字数制限に合わせて行単位で分割する.

        1行がMAX_MESSAGE_LENGTHを超える場合は切り捨て、末尾に通知を付記する。
        空文字列チャンクは生成しない。
        """
        if len(content) <= self.MAX_MESSAGE_LENGTH:
            return [content]

        truncated_suffix = "\n... (切り捨てられました)"
        chunks: list[str] = []
        current_chunk: str | None = None
        for line in content.split("\n"):
            if len(line) > self.MAX_MESSAGE_LENGTH:
                line = (
                    line[: self.MAX_MESSAGE_LENGTH - len(truncated_suffix)]
                    + truncated_suffix
                )

            if current_chunk is not None:
                candidate = current_chunk + "\n" + line
            else:
                candidate = line
            if len(candidate) > self.MAX_MESSAGE_LENGTH:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = candidate
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

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
