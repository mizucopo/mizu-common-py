"""YouTube API HTTPステータスエラー."""

from mizu_common.exceptions.youtube_api_error import YouTubeApiError


class YouTubeHttpError(YouTubeApiError):
    """HTTPステータスエラー（4xx, 5xx）."""

    def __init__(self, message: str, status_code: int) -> None:
        """例外を初期化する.

        Args:
            message: エラーメッセージ
            status_code: HTTPステータスコード
        """
        self.status_code = status_code
        super().__init__(message)
