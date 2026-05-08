"""Discord Webhook関連の例外モジュール."""


class DiscordWebhookError(RuntimeError):
    """Discord Webhook通信エラー.

    Discord Webhookへのリクエストが失敗した場合に発生する。

    Attributes:
        status_code: HTTPステータスコード。接続エラーやタイムアウトの場合はNone。
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
