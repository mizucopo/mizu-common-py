"""YouTube APIネットワークエラー."""

from mizu_common.exceptions.youtube_api_error import YouTubeApiError


class YouTubeNetworkError(YouTubeApiError):
    """ネットワークエラー（接続失敗、タイムアウト等）."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """例外を初期化する.

        Args:
            message: エラーメッセージ
            cause: 元の例外
        """
        self.cause = cause
        super().__init__(message)
