from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

settings = Settings()
