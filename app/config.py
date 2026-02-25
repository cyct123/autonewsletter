from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    pg_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379"

    # AI
    deepseek_api_key: str | None = None
    openai_api_key: str | None = None

    # RSS
    rss_feeds: str = ""

    # Push channels
    wechat_webhook_urls: str = ""
    pushplus_tokens: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    lark_webhook_url: str = ""

    # Whisper transcription
    whisper_url: str = ""
    whisper_model: str = ""
    whisper_timeout: int = 300

    # Scheduling
    weekly_cron: str = "0 9 * * 3"
    immediate_run: bool = False
    force_recent: bool = False

    # Logging
    log_level: str = "info"

    class Config:
        env_file = ".env"


settings = Settings()
