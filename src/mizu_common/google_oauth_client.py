"""Google OAuth認証クライアントモジュール.

Google APIへのアクセスに必要なアクセストークンの取得・管理を提供する。
"""

import logging
import time
from collections.abc import Callable, Sequence
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class GoogleOAuthClient:
    """Google OAuth認証クライアント.

    OAuth Client IDとRefresh Tokenを使用してアクセストークンを取得する。
    スコープは外部から注入され、使用するGoogle APIに応じて柔軟に設定可能。
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"

    def __init__(
        self,
        oauth_client_id: str,
        refresh_token: str,
        scopes: Sequence[str],
        http_post: Optional[Callable[..., requests.Response]] = None,
    ) -> None:
        """クライアントを初期化する.

        Args:
            oauth_client_id: Google OAuth Client ID
            refresh_token: OAuth Refresh Token
            scopes: 要求するGoogle APIスコープのリスト
            http_post: HTTP POST関数（テスト用）
        """
        self._oauth_client_id = oauth_client_id
        self._refresh_token = refresh_token
        self._scopes = scopes
        self._access_token: str | None = None
        self._http_post = http_post or requests.post

    def get_access_token(self) -> str:
        """アクセストークンを取得する.

        必要に応じてリフレッシュトークンを使用して新しいトークンを取得する。

        Returns:
            アクセストークン

        Raises:
            RuntimeError: アクセストークンの取得に失敗した場合
        """
        if self._access_token is None:
            self._refresh_access_token()
        return self._access_token  # type: ignore[return-value]

    def get_headers(self) -> dict[str, str]:
        """Authorizationヘッダーを返す.

        Returns:
            Authorizationヘッダーを含む辞書
        """
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def _refresh_access_token(self) -> None:
        """リフレッシュトークンを使用してアクセストークンを更新する.

        Raises:
            RuntimeError: トークン更新に失敗した場合
        """
        response = self._http_post(
            self.TOKEN_URL,
            data={
                "client_id": self._oauth_client_id,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(f"アクセストークンの取得に失敗しました: {response.text}")

        data = response.json()
        self._access_token = data["access_token"]

    @classmethod
    def authenticate(
        cls,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str],
        output_handler: Optional[Callable[[str], None]] = None,
        http_post: Optional[Callable[..., requests.Response]] = None,
    ) -> Optional[str]:
        """OAuth 2.0 Device Flowを実行してリフレッシュトークンを取得する.

        Args:
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            scopes: 要求するGoogle APIスコープのリスト
            output_handler: 出力ハンドラー（デフォルト: print）
            http_post: HTTP POST関数（テスト用）

        Returns:
            リフレッシュトークン（成功時）、None（失敗時）
        """
        _output_handler = print if output_handler is None else output_handler
        _http_post = http_post or requests.post

        device_code_data = cls._get_device_code(client_id, scopes, _http_post)
        if not device_code_data:
            return None

        device_code = device_code_data["device_code"]
        user_code = device_code_data["user_code"]
        verification_url = device_code_data["verification_url"]
        interval = device_code_data.get("interval", 5)
        expires_in = device_code_data["expires_in"]

        _output_handler(f"\n1. Open your browser and go to: {verification_url}")
        _output_handler(f"2. Enter the following code: {user_code}")
        wait_msg = f"\nWaiting for authentication (expires in {expires_in} seconds)..."
        _output_handler(wait_msg)

        return cls._poll_for_token(
            device_code, client_id, client_secret, interval, expires_in, _http_post
        )

    @classmethod
    def _get_device_code(
        cls,
        client_id: str,
        scopes: Sequence[str],
        http_post: Callable[..., requests.Response],
    ) -> Optional[dict[str, Any]]:
        """Googleからデバイスコードを要求する.

        Args:
            client_id: OAuth クライアント ID
            scopes: 要求するスコープのリスト
            http_post: HTTP POST関数

        Returns:
            デバイスコードレスポンスデータ、失敗時は None
        """
        payload = {"client_id": client_id, "scope": " ".join(scopes)}
        try:
            response = http_post(cls.DEVICE_CODE_URL, data=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except Exception as e:
            logger.error(f"Failed to get device code: {e}")
            return None

    @classmethod
    def _poll_for_token(
        cls,
        device_code: str,
        client_id: str,
        client_secret: str,
        interval: int,
        expires_in: int,
        http_post: Callable[..., requests.Response],
    ) -> Optional[str]:
        """トークンエンドポイントをポーリングする.

        Args:
            device_code: Googleのデバイスコード
            client_id: OAuth クライアント ID
            client_secret: OAuth クライアントシークレット
            interval: ポーリング間隔（秒）
            expires_in: 有効期限（秒）
            http_post: HTTP POST関数

        Returns:
            リフレッシュトークン（成功時）、None（失敗時）
        """
        start_time = time.time()
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        while time.time() - start_time < expires_in:
            try:
                response = http_post(cls.TOKEN_URL, data=payload)
                data: dict[str, Any] = response.json()

                if response.status_code == 200:
                    refresh_token = data.get("refresh_token")
                    if refresh_token:
                        return str(refresh_token)
                    logger.error("No refresh token in successful response.")
                    return None

                error = data.get("error")
                if error == "slow_down":
                    interval += 5
                    logger.debug(f"Slow down requested, new interval: {interval}s")
                elif error == "access_denied":
                    logger.error("Authentication was denied by the user.")
                    return None
                elif error == "expired_token":
                    logger.error("The device code has expired.")
                    return None
                elif error == "authorization_pending":
                    # ユーザーがまだ承認していない、ポーリング継続
                    logger.debug(f"Polling status: {error}")
                elif error is not None:
                    # 未知のエラーは即失敗
                    logger.error(f"Authentication failed: {error}")
                    return None
            except Exception as e:
                logger.error(f"Polling failed: {e}")
                return None

            time.sleep(interval)

        logger.error("Authentication timed out.")
        return None
