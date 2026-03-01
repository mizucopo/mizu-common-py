"""YouTube APIクライアントのテスト."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from mizu_common.exceptions.youtube_http_error import YouTubeHttpError
from mizu_common.exceptions.youtube_network_error import YouTubeNetworkError
from mizu_common.google_oauth_client import GoogleOAuthClient
from mizu_common.youtube_client import YouTubeClient


@pytest.fixture
def mock_oauth_client() -> GoogleOAuthClient:
    """モックされたOAuth認証クライアントを返す."""
    client = Mock(spec=GoogleOAuthClient)
    client.get_headers.return_value = {"Authorization": "Bearer test_token"}
    return client


def test_get_video_details_returns_video_info(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """get_video_detailsが動画情報を返すこと.

    Arrange:
        APIレスポンスをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        YouTubeVideoInfoが正しく返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": "test_video_id",
                "snippet": {
                    "title": "Test Video Title",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            }
        ]
    }
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = client.get_video_details("test_video_id")

    # Assert
    assert result is not None
    assert result.video_id == "test_video_id"
    assert result.title == "Test Video Title"
    assert result.duration == "PT10M"


def test_get_video_details_raises_http_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """HTTPエラー時にget_video_detailsがYouTubeHttpErrorをスローすること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        YouTubeHttpErrorがスローされること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 404
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeHttpError) as exc_info:
        client.get_video_details("nonexistent_id")

    assert exc_info.value.status_code == 404


def test_get_video_details_raises_network_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """ネットワークエラー時にget_video_detailsがYouTubeNetworkErrorをスローすること.

    Arrange:
        ネットワークエラーをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        YouTubeNetworkErrorがスローされること。
    """
    # Arrange
    original_error = requests.exceptions.ConnectionError("Connection failed")
    mocker.patch("requests.get", side_effect=original_error)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeNetworkError) as exc_info:
        client.get_video_details("test_video_id")

    assert exc_info.value.__cause__ == original_error


def test_get_uploads_playlist_id_returns_id(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """_get_uploads_playlist_idがプレイリストIDを返すこと.

    Arrange:
        channels.list APIのレスポンスをモックする。

    Act:
        _get_uploads_playlist_id()を呼び出す。

    Assert:
        uploadsプレイリストIDが返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = client._get_uploads_playlist_id("test_channel_id")

    # Assert
    assert result == "UU_test_playlist_id"


def test_get_uploads_playlist_id_raises_error_for_nonexistent_channel(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """存在しないチャンネルで_get_uploads_playlist_idがValueErrorをスローすること.

    Arrange:
        空のitemsを返すレスポンスをモックする。

    Act:
        _get_uploads_playlist_id()を呼び出す。

    Assert:
        ValueErrorがスローされること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        client._get_uploads_playlist_id("nonexistent_channel_id")

    assert "nonexistent_channel_id" in str(exc_info.value)


def test_iter_playlist_video_ids_yields_ids(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """_iter_playlist_video_idsが動画IDをyieldすること.

    Arrange:
        playlistItems.list APIのレスポンスをモックする。

    Act:
        _iter_playlist_video_ids()からジェネレーターを取得し、リストに変換する。

    Assert:
        動画IDが正しくyieldされること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"contentDetails": {"videoId": "video1"}},
            {"contentDetails": {"videoId": "video2"}},
        ],
        "nextPageToken": None,
    }
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client._iter_playlist_video_ids("test_playlist_id"))

    # Assert
    assert result == ["video1", "video2"]


def test_iter_playlist_video_ids_handles_pagination(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """_iter_playlist_video_idsが複数ページにわたって動画IDをyieldすること.

    Arrange:
        2ページ分のplaylistItems.list APIレスポンスをモックする。

    Act:
        _iter_playlist_video_ids()からジェネレーターを取得し、リストに変換する。

    Assert:
        全ページの動画IDが正しくyieldされること。
    """
    # Arrange
    response_1 = Mock()
    response_1.status_code = 200
    response_1.json.return_value = {
        "items": [{"contentDetails": {"videoId": "video1"}}],
        "nextPageToken": "page2",
    }

    response_2 = Mock()
    response_2.status_code = 200
    response_2.json.return_value = {
        "items": [{"contentDetails": {"videoId": "video2"}}],
        "nextPageToken": None,
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [response_1, response_2]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client._iter_playlist_video_ids("test_playlist_id"))

    # Assert
    assert result == ["video1", "video2"]


def test_iter_channel_videos_yields_videos(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """iter_channel_videosが全動画を正しくyieldすること.

    Arrange:
        channels.list、playlistItems.list、videos.list APIのレスポンスをモックする。

    Act:
        iter_channel_videos()からジェネレーターを取得し、リストに変換する。

    Assert:
        YouTubeVideoInfoが正しくyieldされること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    playlist_response = Mock()
    playlist_response.status_code = 200
    playlist_response.json.return_value = {
        "items": [{"contentDetails": {"videoId": "video1"}}],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Test Video 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [channels_response, playlist_response, videos_response]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client.iter_channel_videos("test_channel_id"))

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video1"
    assert result[0].title == "Test Video 1"


def test_iter_channel_videos_handles_pagination(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """iter_channel_videosが複数ページの動画を正しく処理すること.

    Arrange:
        複数ページのplaylistItems.list APIレスポンスをモックする。

    Act:
        iter_channel_videos()からジェネレーターを取得し、リストに変換する。

    Assert:
        全ページの動画が正しくyieldされること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    playlist_response_1 = Mock()
    playlist_response_1.status_code = 200
    playlist_response_1.json.return_value = {
        "items": [{"contentDetails": {"videoId": "video1"}}],
        "nextPageToken": "page2",
    }

    playlist_response_2 = Mock()
    playlist_response_2.status_code = 200
    playlist_response_2.json.return_value = {
        "items": [{"contentDetails": {"videoId": "video2"}}],
        "nextPageToken": None,
    }

    # 50件未満のため、playlistItemsを全て取得してからvideos.listが呼ばれる
    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Test Video 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            },
            {
                "id": "video2",
                "snippet": {
                    "title": "Test Video 2",
                    "publishedAt": "2024-01-02T00:00:00Z",
                },
                "contentDetails": {"duration": "PT20M"},
            },
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [
        channels_response,
        playlist_response_1,
        playlist_response_2,
        videos_response,
    ]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client.iter_channel_videos("test_channel_id"))

    # Assert
    assert len(result) == 2
    assert result[0].video_id == "video1"
    assert result[1].video_id == "video2"


def test_iter_channel_videos_raises_http_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """HTTPエラー時にiter_channel_videosがYouTubeHttpErrorをスローすること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        iter_channel_videos()から最初の要素を取得しようとする。

    Assert:
        YouTubeHttpErrorがスローされること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 500
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeHttpError) as exc_info:
        next(client.iter_channel_videos("test_channel_id"))

    assert exc_info.value.status_code == 500


def test_iter_channel_videos_raises_network_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """ネットワークエラー時にiter_channel_videosがYouTubeNetworkErrorをスローすること.

    Arrange:
        ネットワークエラーをモックする。

    Act:
        iter_channel_videos()から最初の要素を取得しようとする。

    Assert:
        YouTubeNetworkErrorがスローされること。
    """
    # Arrange
    original_error = requests.exceptions.Timeout("Request timed out")
    mocker.patch("requests.get", side_effect=original_error)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeNetworkError) as exc_info:
        next(client.iter_channel_videos("test_channel_id"))

    assert exc_info.value.__cause__ == original_error


def test_iter_channel_videos_raises_error_on_second_page(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """2ページ目でエラーが発生した場合に遅延して例外がスローされること.

    Arrange:
        1ページ目は成功（50件の動画IDでバッチ処理をトリガー）、
        2ページ目でHTTPエラーが発生するようモックする。

    Act:
        iter_channel_videos()から全要素を取得しようとする。

    Assert:
        1ページ目の動画は取得され、2ページ目の取得時に例外がスローされること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    # 1ページ目に50件の動画IDを設定してバッチ処理をトリガー
    playlist_response_1 = Mock()
    playlist_response_1.status_code = 200
    playlist_response_1.json.return_value = {
        "items": [{"contentDetails": {"videoId": f"video{i}"}} for i in range(50)],
        "nextPageToken": "page2",
    }

    playlist_response_2 = Mock()
    playlist_response_2.status_code = 500

    videos_response_1 = Mock()
    videos_response_1.status_code = 200
    videos_response_1.json.return_value = {
        "items": [
            {
                "id": f"video{i}",
                "snippet": {
                    "title": f"Test Video {i}",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            }
            for i in range(50)
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [
        channels_response,
        playlist_response_1,
        videos_response_1,
        playlist_response_2,
    ]

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    gen = client.iter_channel_videos("test_channel_id")
    first_video = next(gen)
    assert first_video.video_id == "video0"

    with pytest.raises(YouTubeHttpError) as exc_info:
        list(gen)

    assert exc_info.value.status_code == 500


def test_get_channel_videos_returns_list(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """get_channel_videosがリスト形式で動画一覧を返すこと.

    Arrange:
        channels.list、playlistItems.list、videos.list APIのレスポンスをモックする。

    Act:
        get_channel_videos()を呼び出す。

    Assert:
        動画情報のリストが返されること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    playlist_response = Mock()
    playlist_response.status_code = 200
    playlist_response.json.return_value = {
        "items": [
            {"contentDetails": {"videoId": "video1"}},
            {"contentDetails": {"videoId": "video2"}},
        ],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Test Video 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            },
            {
                "id": "video2",
                "snippet": {
                    "title": "Test Video 2",
                    "publishedAt": "2024-01-02T00:00:00Z",
                },
                "contentDetails": {"duration": "PT20M"},
            },
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [channels_response, playlist_response, videos_response]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = client.get_channel_videos("test_channel_id")

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].video_id == "video1"
    assert result[1].video_id == "video2"


def test_iter_channel_videos_with_published_after_filters_old_videos(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """published_afterを指定した場合、閾値より古い動画は返されないこと.

    Arrange:
        異なる公開日時の動画を含むAPIレスポンスをモックする。

    Act:
        published_afterを指定してiter_channel_videos()を呼び出す。

    Assert:
        閾値より新しい動画のみが返されること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    playlist_response = Mock()
    playlist_response.status_code = 200
    playlist_response.json.return_value = {
        "items": [
            {"contentDetails": {"videoId": "video1"}},
            {"contentDetails": {"videoId": "video2"}},
            {"contentDetails": {"videoId": "video3"}},
        ],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "New Video",
                    "publishedAt": "2024-03-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            },
            {
                "id": "video2",
                "snippet": {
                    "title": "Threshold Video",
                    "publishedAt": "2024-02-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            },
            {
                "id": "video3",
                "snippet": {
                    "title": "Old Video",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            },
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [channels_response, playlist_response, videos_response]

    client = YouTubeClient(mock_oauth_client)
    published_after = datetime(2024, 2, 1, tzinfo=timezone.utc)

    # Act
    result = list(client.iter_channel_videos("test_channel_id", published_after))

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video1"


def test_iter_channel_videos_with_published_after_stops_early(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """published_afterを指定した場合、古い動画に達したら早期終了すること.

    Arrange:
        50件の動画IDを含むプレイリストと、バッチ処理用の動画詳細をモックする。
        動画詳細には新しい順に並んでおり、閾値より古い動画で終了する。

    Act:
        published_afterを指定してiter_channel_videos()を呼び出す。

    Assert:
        古い動画に達した時点でジェネレーターが終了すること。
    """
    # Arrange
    channels_response = Mock()
    channels_response.status_code = 200
    channels_response.json.return_value = {
        "items": [
            {"contentDetails": {"relatedPlaylists": {"uploads": "UU_test_playlist_id"}}}
        ]
    }

    # 50件の動画IDでバッチ処理をトリガー
    playlist_response = Mock()
    playlist_response.status_code = 200
    playlist_response.json.return_value = {
        "items": [{"contentDetails": {"videoId": f"video{i}"}} for i in range(50)],
        "nextPageToken": "page2",
    }

    # 動画詳細: video0は新しい、video1以降は閾値より古い
    videos_response = Mock()
    videos_response.status_code = 200
    video_items = [
        {
            "id": "video0",
            "snippet": {
                "title": "New Video",
                "publishedAt": "2024-03-01T00:00:00Z",
            },
            "contentDetails": {"duration": "PT10M"},
        }
    ]
    # 残り49件は閾値と同時刻（含まれない）
    for i in range(1, 50):
        video_items.append(
            {
                "id": f"video{i}",
                "snippet": {
                    "title": f"Old Video {i}",
                    "publishedAt": "2024-02-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            }
        )
    videos_response.json.return_value = {"items": video_items}

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [channels_response, playlist_response, videos_response]

    client = YouTubeClient(mock_oauth_client)
    published_after = datetime(2024, 2, 1, tzinfo=timezone.utc)

    # Act
    result = list(client.iter_channel_videos("test_channel_id", published_after))

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video0"
    # 2ページ目はリクエストされないこと
    assert mock_get.call_count == 3
