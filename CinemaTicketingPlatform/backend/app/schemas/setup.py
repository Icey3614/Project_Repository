from pydantic import BaseModel, Field


class SetupDatabase(BaseModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=100)
    port: int = Field(default=3306, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(default="", max_length=200)
    db_name: str = Field(default="cinema_platform", min_length=1, max_length=64)


class SetupAlipay(BaseModel):
    app_id: str = Field(default="", max_length=64)
    private_key: str = Field(default="", max_length=4096)
    public_key: str = Field(default="", max_length=2048)
    notify_url: str = Field(default="", max_length=500)
