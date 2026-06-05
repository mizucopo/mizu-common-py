"""ロック付きファイル操作が依存する provider の型定義。"""

from typing import Any, Protocol


class _LockedFileOperationsProvider(Protocol):
    """_LockedFileOperations が利用する provider の最小インターフェース。"""

    CHUNK_SIZE: int
    MAX_RETRIES: int
    folder_id: str
    service: Any

    def sanitize_name(self, name: str) -> str: ...

    def _find_folder_path(self, path_parts: list[str]) -> str | None: ...

    def _ensure_folder_path(self, path_parts: list[str]) -> str: ...
