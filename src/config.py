from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class AppConfig(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    backend_url: str = "http://localhost:8000"
    request_timeout: float = 10.0
    page_size: int = 20


config = AppConfig()
