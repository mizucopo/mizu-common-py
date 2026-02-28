"""Discord Webhook関連の例外モジュール."""


class DiscordWebhookError(RuntimeError):
    """Discord Webhook通信エラー.

    Discord Webhookへのリクエストが失敗した場合に発生する。
    """

    pass
