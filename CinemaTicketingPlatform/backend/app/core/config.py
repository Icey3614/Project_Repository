from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "Cinema Ticketing Platform"
    API_PREFIX: str = "/api/v1"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "cinema_platform"

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    CORS_ORIGINS: str = "http://localhost:5173"
    TZ: str = "Asia/Shanghai"
    PAYMENT_PROVIDER: str = "mock"
    SCHEDULER_ENABLED: bool = True

    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_NOTIFY_URL: str = ""
    ALIPAY_RETURN_URL: str = "http://localhost:5173/me"
    ALIPAY_GATEWAY: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    FRONTEND_DIST: str = ""

    @property
    def frontend_dist_path(self) -> str | None:
        if self.FRONTEND_DIST:
            return self.FRONTEND_DIST
        from pathlib import Path

        candidate = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
        return str(candidate) if candidate.exists() else None

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
