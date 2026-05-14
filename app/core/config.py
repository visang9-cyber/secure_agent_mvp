from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Secure Agent MVP"
    debug: bool = False
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
