import httpx
from typing import Any, Optional


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._token: Optional[str] = None
        self._client: Optional[httpx.Client] = None

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, value: Optional[str]):
        self._token = value
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    def set_base_url(self, url: str):
        self.base_url = url.rstrip("/")
        if self._client:
            self._client.close()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code == 204:
            return None
        if 200 <= response.status_code < 300:
            return response.json()
        try:
            data = response.json()
            detail = data.get("detail", response.text)
        except Exception:
            detail = response.text
        raise ApiError(response.status_code, detail)

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        response = self.client.get(path, params=params)
        return self._handle_response(response)

    def post(self, path: str, json: Optional[dict] = None, data: Optional[dict] = None) -> Any:
        response = self.client.post(path, json=json, data=data)
        return self._handle_response(response)

    def put(self, path: str, json: Optional[dict] = None) -> Any:
        response = self.client.put(path, json=json)
        return self._handle_response(response)

    def delete(self, path: str) -> Any:
        response = self.client.delete(path)
        return self._handle_response(response)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
