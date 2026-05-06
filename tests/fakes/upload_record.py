from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UploadRecord:
    """アップロード操作の記録。"""

    name: str
    parent_id: str
    operation: str  # "create_file" | "create_folder" | "update_file"
    id: str = ""
