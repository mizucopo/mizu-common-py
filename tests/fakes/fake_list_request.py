from __future__ import annotations

import re
from typing import Any


class FakeListRequest:
    """files().list(q=...).execute() のfake。"""

    def __init__(self, service: Any, kwargs: dict[str, Any]) -> None:
        self._service = service
        self._kwargs = kwargs

    def execute(self) -> dict[str, Any]:
        with self._service._state_lock:
            if self._service._list_errors:
                raise self._service._list_errors.pop(0)

            query = self._kwargs.get("q", "")
            name, parent_id, is_folder = self._parse_query(query)
            store = self._service._folders if is_folder else self._service._files

            results: list[dict[str, str]] = []
            for (pid, n), entry in store.items():
                if name and n != name:
                    continue
                if parent_id and pid != parent_id:
                    continue
                results.append(entry)

            return {"files": results}

    @staticmethod
    def _parse_query(query: str) -> tuple[str, str, bool]:
        name = ""
        parent_id = ""
        is_folder = False

        name_match = re.search(r"name\s*=\s*'([^']*)'", query)
        if name_match:
            name = name_match.group(1)

        parent_match = re.search(r"'([^']+)'\s+in\s+parents", query)
        if parent_match:
            parent_id = parent_match.group(1)

        if "mimeType" in query:
            is_folder = True

        return name, parent_id, is_folder
