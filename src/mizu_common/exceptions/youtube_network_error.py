"""YouTube APIネットワークエラー."""

from mizu_common.exceptions.youtube_api_error import YouTubeApiError


class YouTubeNetworkError(YouTubeApiError):
    """ネットワークエラー（接続失敗、タイムアウト等）."""
