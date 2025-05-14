from typing import Tuple, Type, List

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    title: str = "CPM AI"
    description: str = "CPM AI API"
    debug: bool = True
    version: str = "0.0.1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    doc_username: str = "admin"
    doc_password: str = "admin"

    auth_algorithm: str = "HS256"
    jwks_url: str | None = None
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    allowed_file_extensions: set = {"pdf"}
    s3_bucket: str = "cpm-raw-docs"
    aws_region: str = "us-east-1"
    s3_region: str = "us-east-1"
    sqs_queue_url: str
    mongodb_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter=".",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            dotenv_settings,
            env_settings,
            init_settings,
        )
