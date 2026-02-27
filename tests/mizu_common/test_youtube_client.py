"""YouTube APIクライアントのテスト."""

from typing import Any
from unittest.mock import Mock

import pytest

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


def test_get_video_details_returns_none_on_error(
    mocker: Any, mock_oauth_client: GoogleOAuthClient
) -> None:
    """APIエラー時にget_video_detailsがNoneを返すこと.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 404
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient(mock_oauth_client)

    # Act
    result = client.get_video_details("nonexistent_id")

    # Assert
    assert result is None


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
