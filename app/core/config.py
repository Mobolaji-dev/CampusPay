from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NOMBA_CLIENT_ID:str
    NOMBA_PRIVATE_KEY:str
    NOMBA_ACCOUNT_ID:str
    NOMBA_SUB_ACCOUNT_ID: str
    NOMBA_BASE_URL:str
    DATABASE_URL:str
    SECRET_KEY:str
    GOOGLE_PROJECT_ID: str
    GOOGLE_CLIENT_EMAIL:str
    GOOGLE_PRIVATE_KEY:str
    FIREBASE_CREDENTIALS_PATH:str
    TOKEN_URL:str
    WEBHOOK_SECRET:str
    

    class Config:
        env_file= ".env"

settings=Settings()