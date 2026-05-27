from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/health_assistant"
    )

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    # If unset, boto3 falls back to its default credential chain
    # (~/.aws/credentials, instance profile, etc.).
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    PRESIGNED_URL_EXPIRY_SECONDS: int = 300


settings = Settings()
