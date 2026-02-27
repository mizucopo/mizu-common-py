"""YouTube動画情報を表すデータモデル."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class YouTubeVideoInfo:
    """YouTube動画情報を表すデータクラス."""

    video_id: str
    title: str
    published_at: datetime
    duration: str
