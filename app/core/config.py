from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
   
    APP_NAME: str = "LinguaAI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    
    DATABASE_URL: str

  
    REDIS_URL: str = "redis://localhost:6379/0"

   
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "linguaai-audio"


    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    #  Email (for forgot password)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "LinguaAI"

    # AI
   
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE: str = "cpu"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"



settings = Settings()