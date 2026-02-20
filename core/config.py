from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HF_IMAGE_MODEL: str | None = None
    HF_VIDEO_MODEL: str | None = None
    NGC_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

settings = Settings()
