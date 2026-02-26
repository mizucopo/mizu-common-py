"""Google API スコープ."""

from enum import Enum


class GoogleScope(str, Enum):
    """Google API スコープ."""

    YOUTUBE_READONLY = "https://www.googleapis.com/auth/youtube.readonly"
    DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
