"""YouTube Data API v3クライアントモジュール.

チャンネルの全動画（ライブ含む）の取得を提供する。
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import requests

from mizu_common.constants.http_timeout import DEFAULT_TIMEOUT
from mizu_common.exceptions.youtube_http_error import YouTubeHttpError
from mizu_common.exceptions.youtube_network_error import YouTubeNetworkError
from mizu_common.google_oauth_client import GoogleOAuthClient
from mizu_common.models.youtube_video_info import YouTubeVideoInfo


class YouTubeClient:
    """YouTube Data API v3クライアント.

    OAuth認証を使用してYouTube APIにアクセスし、チャンネルの全動画情報を取得する。
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    MAX_RESULTS_PER_PAGE = 50

    # APIエンドポイント
    ENDPOINT_CHANNELS = "channels"
    ENDPOINT_PLAYLIST_ITEMS = "playlistItems"
    ENDPOINT_VIDEOS = "videos"

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
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise YouTubeNetworkError(f"APIリクエストに失敗しました: {e}") from e

        if response.status_code != 200:
            raise YouTubeHttpError(
                f"APIリクエストが失敗しました: status={response.status_code}, "
                f"endpoint={endpoint}",
                status_code=response.status_code,
            )

        return cast("dict[str, Any]", response.json())

    def _get_uploads_playlist_id(self, channel_id: str) -> str:
        """チャンネルIDからuploadsプレイリストIDを取得する.

        Args:
            channel_id: YouTubeチャンネルID

        Returns:
            uploadsプレイリストID

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
            ValueError: チャンネルが見つからない場合
        """
        params = {
            "part": "contentDetails",
            "id": channel_id,
        }

        data = self._make_request(self.ENDPOINT_CHANNELS, params)

        items = data.get("items", [])
        if not items:
            raise ValueError(f"チャンネルが見つかりません: {channel_id}")

        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return str(uploads_id)

    def _iter_playlist_video_ids(self, playlist_id: str) -> Iterator[str]:
        """プレイリスト内の動画IDを順次取得するジェネレーター.

        Args:
            playlist_id: プレイリストID

        Yields:
            動画ID

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合

        Note:
            例外は遅延して発生する可能性があります。
            2ページ目以降の取得時にエラーが発生した場合、
            そのページの最初の動画IDを取得しようとしたタイミングで例外が送出されます。
        """
        next_page_token: str | None = None

        while True:
            params: dict[str, str] = {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": str(self.MAX_RESULTS_PER_PAGE),
            }

            if next_page_token:
                params["pageToken"] = next_page_token

            data = self._make_request(self.ENDPOINT_PLAYLIST_ITEMS, params)

            for item in data.get("items", []):
                video_id = item["contentDetails"]["videoId"]
                yield video_id

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    def iter_channel_videos(
        self, channel_id: str, published_after: datetime | None = None
    ) -> Iterator[YouTubeVideoInfo]:
        """チャンネルの全動画（ライブ含む）を順次取得するジェネレーター.

        Args:
            channel_id: YouTubeチャンネルID
            published_after: この日時以降の動画のみ取得（Noneの場合は全件取得）

        Yields:
            YouTubeVideoInfo: 動画情報

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
            ValueError: チャンネルが見つからない場合

        Note:
            uploadsプレイリストはアップロード順（新しい順）で返されることを前提とします。
            published_afterを指定した場合、閾値より古い動画に達した時点で終了します。
            例外は遅延して発生する可能性があります。
            2ページ目以降の取得時にエラーが発生した場合、
            そのページの最初の動画を取得しようとしたタイミングで例外が送出されます。
        """
        playlist_id = self._get_uploads_playlist_id(channel_id)

        video_ids_batch: list[str] = []
        for video_id in self._iter_playlist_video_ids(playlist_id):
            video_ids_batch.append(video_id)

            # MAX_RESULTS_PER_PAGE件ずつバッチ処理
            if len(video_ids_batch) >= self.MAX_RESULTS_PER_PAGE:
                videos = self._get_video_details_batch(video_ids_batch)
                for video in videos:
                    if published_after and video.published_at < published_after:
                        return
                    yield video
                video_ids_batch = []

        # 残りの動画を処理
        if video_ids_batch:
            videos = self._get_video_details_batch(video_ids_batch)
            for video in videos:
                if published_after and video.published_at < published_after:
                    return
                yield video

    def get_channel_videos(
        self, channel_id: str, published_after: datetime | None = None
    ) -> list[YouTubeVideoInfo]:
        """チャンネルの全動画（ライブ含む）一覧を取得する.

        Args:
            channel_id: YouTubeチャンネルID
            published_after: この日時以降の動画のみ取得（Noneの場合は全件取得）

        Returns:
            動画情報のリスト

        Raises:
            YouTubeNetworkError: ネットワークエラーが発生した場合
            YouTubeHttpError: HTTPステータスエラーが発生した場合
            ValueError: チャンネルが見つからない場合
        """
        return list(self.iter_channel_videos(channel_id, published_after))

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

        data = self._make_request(self.ENDPOINT_VIDEOS, params)

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

        Note:
            YouTube Data API v3には単一動画取得の専用エンドポイントはなく、
            videos.list エンドポイントでIDを指定して取得する仕様。
            そのため内部的にバッチ取得メソッドを使用してもAPIリクエスト数は同じであり、
            コードの再利用性を高めるために_get_video_details_batchを使用している。
        """
        videos = self._get_video_details_batch([video_id])
        return videos[0] if videos else None
