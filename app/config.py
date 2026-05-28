from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/health_assistant"
    )

    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.5-pro"

    # If unset, boto3 falls back to its default credential chain
    # (~/.aws/credentials, instance profile, etc.).
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    PRESIGNED_URL_EXPIRY_SECONDS: int = 300

    # Arize tracing
    ARIZE_API_KEY: Optional[str] = None
    ARIZE_SPACE_ID: Optional[str] = None
    ARIZE_COLLECTOR_ENDPOINT: str = "https://otlp.arize.com"
    ARIZE_PROJECT_NAME: str = "health-assistant"


settings = Settings()
