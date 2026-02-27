"""YouTube Data API v3クライアントモジュール.

YouTubeライブアーカイブの検出と詳細取得を提供する。
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import requests

from mizu_common.exceptions.youtube_http_error import YouTubeHttpError
from mizu_common.exceptions.youtube_network_error import YouTubeNetworkError
from mizu_common.google_oauth_client import GoogleOAuthClient
from mizu_common.models.youtube_video_info import YouTubeVideoInfo


class YouTubeClient:
    """YouTube Data API v3クライアント.

    OAuth認証を使用してYouTube APIにアクセスし、ライブアーカイブ情報を取得する。
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, oauth_client: GoogleOAuthClient) -> None:
        """クライアントを初期化する.

        Args:
            oauth_client: Google OAuth認証クライアント
        """
        self._oauth_client = oauth_client

    def _make_request(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        """APIリクエストを実行する.

        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ

        Returns:
            レスポンスJSON

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
        """
        headers = self._oauth_client.get_headers()
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise YouTubeNetworkError(
                f"APIリクエストに失敗しました: {e}", cause=e
            ) from e

        if response.status_code != 200:
            raise YouTubeHttpError(
                f"APIリクエストが失敗しました: status={response.status_code}, "
                f"endpoint={endpoint}",
                status_code=response.status_code,
            )

        return cast("dict[str, Any]", response.json())

    def iter_live_archives(self, channel_id: str) -> Iterator[YouTubeVideoInfo]:
        """チャンネルのライブアーカイブを順次取得するジェネレーター.

        Args:
            channel_id: YouTubeチャンネルID

        Yields:
            YouTubeVideoInfo: ライブアーカイブ情報

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合

        Note:
            例外は遅延して発生する可能性があります。
            2ページ目以降の取得時にエラーが発生した場合、
            そのページの最初の動画を取得しようとしたタイミングで例外が送出されます。
        """
        next_page_token: str | None = None

        while True:
            params: dict[str, str] = {
                "channelId": channel_id,
                "part": "id",
                "maxResults": "50",
                "type": "video",
                "eventType": "completed",
            }

            if next_page_token:
                params["pageToken"] = next_page_token

            data = self._make_request("search", params)

            video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
            if video_ids:
                video_details = self._get_video_details_batch(video_ids)
                yield from video_details

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    def get_live_archives(self, channel_id: str) -> list[YouTubeVideoInfo]:
        """チャンネルのライブアーカイブ一覧を取得する."""
        return list(self.iter_live_archives(channel_id))

    def _get_video_details_batch(self, video_ids: list[str]) -> list[YouTubeVideoInfo]:
        """複数の動画詳細を一括取得する.

        Args:
            video_ids: 動画IDのリスト

        Returns:
            動画情報のリスト

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
        """
        if not video_ids:
            return []

        params = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_ids),
        }

        data = self._make_request("videos", params)

        videos: list[YouTubeVideoInfo] = []
        for item in data.get("items", []):
            video_id = item["id"]
            title = item["snippet"]["title"]
            published_at_str = item["snippet"]["publishedAt"]
            duration = item["contentDetails"]["duration"]

            # ISO 8601形式の日時をパース
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )

            videos.append(
                YouTubeVideoInfo(
                    video_id=video_id,
                    title=title,
                    published_at=published_at,
                    duration=duration,
                )
            )

        return videos

    def get_video_details(self, video_id: str) -> YouTubeVideoInfo | None:
        """単一の動画詳細を取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            動画情報（存在しない場合はNone）

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
        """
        videos = self._get_video_details_batch([video_id])
        return videos[0] if videos else None
