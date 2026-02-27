"""YouTube APIクライアントのテスト."""

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


def test_make_request_raises_http_error_on_non_200(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """_make_requestが非200レスポンスでYouTubeHttpErrorをスローすること.

    Arrange:
        404エラーレスポンスをモックする。

    Act:
        _make_request()を呼び出す。

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
        client._make_request("videos", {"id": "test_id"})

    assert exc_info.value.status_code == 404


def test_make_request_raises_network_error_on_connection_failure(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """_make_requestが接続エラーでYouTubeNetworkErrorをスローすること.

    Arrange:
        接続エラーをモックする。

    Act:
        _make_request()を呼び出す。

    Assert:
        YouTubeNetworkErrorがスローされること。
    """
    # Arrange
    original_error = requests.exceptions.ConnectionError("Connection failed")
    mocker.patch("requests.get", side_effect=original_error)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeNetworkError) as exc_info:
        client._make_request("videos", {"id": "test_id"})

    assert exc_info.value.__cause__ == original_error


def test_get_live_archives_returns_videos(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """get_live_archivesがライブアーカイブ一覧を返すこと.

    Arrange:
        検索APIと動画詳細APIのレスポンスをモックする。

    Act:
        get_live_archives()を呼び出す。

    Assert:
        YouTubeVideoInfoのリストが返されること。
    """
    # Arrange
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "items": [{"id": {"videoId": "video1"}}],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Live Archive 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT1H"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [search_response, videos_response]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = client.get_live_archives("test_channel_id")

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video1"
    assert result[0].title == "Live Archive 1"


def test_get_live_archives_raises_http_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """HTTPエラー時にget_live_archivesがYouTubeHttpErrorをスローすること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_live_archives()を呼び出す。

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
        client.get_live_archives("test_channel_id")

    assert exc_info.value.status_code == 500


def test_get_live_archives_raises_network_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """ネットワークエラー時にget_live_archivesがYouTubeNetworkErrorをスローすること.

    Arrange:
        ネットワークエラーをモックする。

    Act:
        get_live_archives()を呼び出す。

    Assert:
        YouTubeNetworkErrorがスローされること。
    """
    # Arrange
    original_error = requests.exceptions.Timeout("Request timed out")
    mocker.patch("requests.get", side_effect=original_error)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeNetworkError) as exc_info:
        client.get_live_archives("test_channel_id")

    assert exc_info.value.__cause__ == original_error


def test_iter_live_archives_yields_videos(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """iter_live_archivesが単一ページの動画を正しくyieldすること.

    Arrange:
        検索APIと動画詳細APIのレスポンスをモックする。

    Act:
        iter_live_archives()からジェネレーターを取得し、リストに変換する。

    Assert:
        YouTubeVideoInfoが正しくyieldされること。
    """
    # Arrange
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "items": [{"id": {"videoId": "video1"}}],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Live Archive 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT1H"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [search_response, videos_response]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client.iter_live_archives("test_channel_id"))

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video1"
    assert result[0].title == "Live Archive 1"


def test_iter_live_archives_handles_pagination(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """iter_live_archivesが複数ページにわたって動画をyieldすること.

    Arrange:
        2ページ分の検索APIレスポンスと動画詳細APIレスポンスをモックする。

    Act:
        iter_live_archives()からジェネレーターを取得し、リストに変換する。

    Assert:
        全ページの動画が正しくyieldされること。
    """
    # Arrange
    search_response_1 = Mock()
    search_response_1.status_code = 200
    search_response_1.json.return_value = {
        "items": [{"id": {"videoId": "video1"}}],
        "nextPageToken": "page2",
    }

    search_response_2 = Mock()
    search_response_2.status_code = 200
    search_response_2.json.return_value = {
        "items": [{"id": {"videoId": "video2"}}],
        "nextPageToken": None,
    }

    videos_response_1 = Mock()
    videos_response_1.status_code = 200
    videos_response_1.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Live Archive 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT1H"},
            }
        ]
    }

    videos_response_2 = Mock()
    videos_response_2.status_code = 200
    videos_response_2.json.return_value = {
        "items": [
            {
                "id": "video2",
                "snippet": {
                    "title": "Live Archive 2",
                    "publishedAt": "2024-01-02T00:00:00Z",
                },
                "contentDetails": {"duration": "PT2H"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [
        search_response_1,
        videos_response_1,
        search_response_2,
        videos_response_2,
    ]

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = list(client.iter_live_archives("test_channel_id"))

    # Assert
    assert len(result) == 2
    assert result[0].video_id == "video1"
    assert result[1].video_id == "video2"


def test_iter_live_archives_raises_http_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """HTTPエラー時にiter_live_archivesがYouTubeHttpErrorをスローすること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        iter_live_archives()から最初の要素を取得しようとする。

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
        next(client.iter_live_archives("test_channel_id"))

    assert exc_info.value.status_code == 500


def test_iter_live_archives_raises_network_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """ネットワークエラー時にiter_live_archivesがYouTubeNetworkErrorをスローすること.

    Arrange:
        ネットワークエラーをモックする。

    Act:
        iter_live_archives()から最初の要素を取得しようとする。

    Assert:
        YouTubeNetworkErrorがスローされること。
    """
    # Arrange
    original_error = requests.exceptions.Timeout("Request timed out")
    mocker.patch("requests.get", side_effect=original_error)

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    with pytest.raises(YouTubeNetworkError) as exc_info:
        next(client.iter_live_archives("test_channel_id"))

    assert exc_info.value.__cause__ == original_error


def test_iter_live_archives_raises_error_on_second_page(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """2ページ目でエラーが発生した場合に遅延して例外がスローされること.

    Arrange:
        1ページ目は成功、2ページ目でHTTPエラーが発生するようモックする。

    Act:
        iter_live_archives()から全要素を取得しようとする。

    Assert:
        1ページ目の動画は取得され、2ページ目の取得時に例外がスローされること。
    """
    # Arrange
    search_response_1 = Mock()
    search_response_1.status_code = 200
    search_response_1.json.return_value = {
        "items": [{"id": {"videoId": "video1"}}],
        "nextPageToken": "page2",
    }

    search_response_2 = Mock()
    search_response_2.status_code = 500

    videos_response_1 = Mock()
    videos_response_1.status_code = 200
    videos_response_1.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Live Archive 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT1H"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [
        search_response_1,
        videos_response_1,
        search_response_2,
    ]

    client = YouTubeClient(mock_oauth_client)

    # Act & Assert
    gen = client.iter_live_archives("test_channel_id")
    first_video = next(gen)
    assert first_video.video_id == "video1"

    with pytest.raises(YouTubeHttpError) as exc_info:
        list(gen)

    assert exc_info.value.status_code == 500
