"""Google Drive アップロードプロバイダモジュール。"""

import logging
import re
import threading
from contextlib import contextmanager
from typing import Any, Generator

from google.oauth2 import credentials
from googleapiclient.discovery import build

from mizu_common.constants.google_scope import GoogleScope
from mizu_common.google_drive._locked_file_operations import _LockedFileOperations

logger = logging.getLogger(__name__)


class GoogleDriveProvider:
    """OAuth 2.0 トークンを使用した Google Drive アップロードプロバイダ。

    同名ファイルが存在する場合は更新、存在しない場合は新規作成する。
    """

    CHUNK_SIZE = 100 * 1024 * 1024
    MAX_RETRIES = 5
    SCOPES = [GoogleScope.DRIVE_FILE]

    # サニタイズ用定数
    SANITIZE_PATTERN = r'[\\:*?"<>|\r\n\t]'
    SANITIZE_REPLACEMENT = "_"

    # Google Drive mimeType
    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Google Drive で使用できない文字を置換する。

        パス区切り（/）は除外し、ファイル名・フォルダ名として使用できない文字のみ置換する。

        Args:
            name: 元の名前

        Returns:
            サニタイズされた名前
        """
        # 禁止文字: \ : * ? " < > | と制御文字（/ はパス区切りとして使用するため除外）
        sanitized = re.sub(GoogleDriveProvider.SANITIZE_PATTERN, "_", name)
        # 先頭・末尾のドットとスペースを削除
        sanitized = sanitized.strip(". ")
        return sanitized if sanitized else "untitled"

    def __init__(
        self,
        folder_id: str,
        credentials: credentials.Credentials,
        drive_service: Any | None = None,
    ) -> None:
        """Google Drive アップロードプロバイダを初期化する。

        Args:
            folder_id: Google Drive フォルダ ID
            credentials: OAuth 2.0 認証情報
            drive_service: Google Drive API サービス（テスト用）
        """
        self.folder_id = folder_id
        self.creds = credentials
        self.service = drive_service or build("drive", "v3", credentials=credentials)
        self._file_locks: dict[str, threading.Lock] = {}
        self._folder_locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()  # ロック辞書の保護用

    @classmethod
    def from_credentials(
        cls,
        folder_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> "GoogleDriveProvider":
        """認証情報から GoogleDriveProvider を作成（ファクトリメソッド）。

        Args:
            folder_id: Google Drive フォルダ ID
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            refresh_token: OAuth リフレッシュトークン

        Returns:
            GoogleDriveProvider インスタンス
        """
        creds = credentials.Credentials(
            token=None,  # 初回使用時に更新される
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=cls.SCOPES,
        )  # type: ignore[no-untyped-call]

        return cls(folder_id=folder_id, credentials=creds)

    @contextmanager
    def _file_lock(self, filename: str) -> Generator[None, None, None]:
        """指定されたファイル名に対するロックを取得するコンテキストマネージャ。

        ロック解放時に辞書からエントリを削除してメモリリークを防ぐ。

        注意:
            このロックの内側で _folder_lock が取得される場合がある。
            ロック取得順序は常に _file_lock → _folder_lock の順でなければならない。
            逆順での取得はデッドロックを引き起こす可能性がある。

        Args:
            filename: ファイル名
        """
        with self._locks_lock:
            lock = self._file_locks.setdefault(filename, threading.Lock())

        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with self._locks_lock:
                # 他のスレッドが既に削除している可能性があるため、存在確認なしで削除
                self._file_locks.pop(filename, None)

    @contextmanager
    def _folder_lock(self, folder_path: str) -> Generator[None, None, None]:
        """指定されたフォルダパスに対するロックを取得するコンテキストマネージャ。

        異なるファイル名で同じフォルダパスを使用する場合の競合を防ぐ。
        ロック解放時に辞書からエントリを削除してメモリリークを防ぐ。

        注意:
            このロックは常に _file_lock の内側でのみ取得される。
            ロック取得順序: _file_lock → _folder_lock（逆順は禁止）

        Args:
            folder_path: フォルダパス（例: "folder/sub"）
        """
        with self._locks_lock:
            lock = self._folder_locks.setdefault(folder_path, threading.Lock())

        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with self._locks_lock:
                # 他のスレッドが既に削除している可能性があるため、存在確認なしで削除
                self._folder_locks.pop(folder_path, None)

    def upload(self, source_path: str, destination_filename: str) -> None:
        """Google Drive にファイルをアップロードする。

        同名ファイルが存在する場合は上書き、存在しない場合は新規作成する。
        MediaFileUpload によるチャンキングと next_chunk によるリトライを実装。

        スレッドセーフ:
            同一ファイル名への並行アップロードは直列化される。
            同一フォルダパスへの並行アクセスも直列化される。
            ロック取得順序: _file_lock → _folder_lock

        Args:
            source_path: ローカルファイルパス
            destination_filename: Google Drive 上のファイル名

        Raises:
            RuntimeError: アップロード失敗時
        """
        with self._file_lock(destination_filename):
            logger.info(
                f"Uploading {source_path} to Google Drive folder {self.folder_id} "
                f"as {destination_filename}..."
            )

            ops = _LockedFileOperations(self)
            existing_file_id = ops.search_for_file(destination_filename)

            if existing_file_id:
                ops.update_file(existing_file_id, source_path)
            else:
                ops.create_file(source_path, destination_filename)

    def _find_folder(self, name: str, parent_id: str) -> str | None:
        """指定した親フォルダ内でフォルダを検索する。

        Args:
            name: 検索するフォルダ名
            parent_id: 親フォルダID

        Returns:
            フォルダID（存在する場合）、None（存在しない場合）
        """
        escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType = '{self.FOLDER_MIME_TYPE}' and "
            f"trashed = false"
        )
        logger.debug(f"Searching for folder '{name}' in parent '{parent_id}'")
        results = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id)")
            .execute()
        )
        files = results.get("files", [])
        if files:
            folder_id = str(files[0]["id"])
            logger.debug(f"Found folder '{name}' (ID: {folder_id})")
            return folder_id
        logger.debug(f"Folder '{name}' not found in parent '{parent_id}'")
        return None

    def _create_folder(self, name: str, parent_id: str) -> str:
        """フォルダを作成し、フォルダIDを返す。

        Args:
            name: 作成するフォルダ名
            parent_id: 親フォルダID

        Returns:
            作成されたフォルダのID
        """
        logger.info(f"Creating folder '{name}' in parent '{parent_id}'")
        file_metadata = {
            "name": name,
            "parents": [parent_id],
            "mimeType": self.FOLDER_MIME_TYPE,
        }
        result = (
            self.service.files()
            .create(
                body=file_metadata,  # type: ignore[arg-type]
                fields="id",
            )
            .execute()
        )
        folder_id = str(result.get("id"))
        logger.info(f"Created folder '{name}' (ID: {folder_id})")
        return folder_id

    def _ensure_folder_path(self, path_parts: list[str]) -> str:
        """フォルダパスを確保し、最終的なフォルダIDを返す。

        存在しないフォルダは新規作成する。
        同じフォルダパスへ同時にアクセスする場合の競合を防ぐためロックを使用する。

        注意:
            このメソッドは _folder_lock を取得するため、
            必ず _file_lock の内側で呼ぶこと。

        Args:
            path_parts: フォルダ名のリスト（例: ["folder", "subfolder"]）

        Returns:
            最終的なフォルダID
        """
        folder_path = "/".join(path_parts)
        with self._folder_lock(folder_path):
            logger.info(f"Ensuring folder path: {folder_path}")
            current_parent_id = self.folder_id

            for folder_name in path_parts:
                sanitized_name = self.sanitize_name(folder_name)
                folder_id = self._find_folder(sanitized_name, current_parent_id)
                if folder_id is None:
                    folder_id = self._create_folder(sanitized_name, current_parent_id)
                current_parent_id = folder_id

            logger.info(f"Folder path resolved to ID: {current_parent_id}")
            return current_parent_id

    def _find_folder_path(self, path_parts: list[str]) -> str | None:
        """フォルダパスを検索し、存在すれば最終フォルダIDを返す。

        Args:
            path_parts: フォルダ名のリスト

        Returns:
            最終フォルダID（存在する場合）、None（存在しない場合）
        """
        current_parent_id = self.folder_id

        for folder_name in path_parts:
            sanitized_name = self.sanitize_name(folder_name)
            folder_id = self._find_folder(sanitized_name, current_parent_id)
            if folder_id is None:
                return None
            current_parent_id = folder_id

        return current_parent_id
