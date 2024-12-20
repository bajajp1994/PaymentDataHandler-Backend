import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_uri: str
    database_name: str
    
    class Config:
        env_file = ".env"  # Load settings from .env file
        extra = "allow"

settings = Settings()
