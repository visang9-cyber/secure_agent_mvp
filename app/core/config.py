from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Secure Agent MVP"
    debug: bool = False

    openai_api_key: str = ""
    openai_model: str = "gpt-4.5"

    weather_api_key: str = ""
    weather_api_provider: str = "openweathermap"

    schedule_seed: int = 42
    schedule_msa_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
