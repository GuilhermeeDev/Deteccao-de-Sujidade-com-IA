import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Primeiro tenta puxar do .env, caso nao conseguir, o segundo valor "default" eh usado.
class Settings:
    
    # GitHub ou Local
    REPOSITORIO: str = os.getenv("REPOSITORIO", "local")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    REPO_OWNER: str = os.getenv("REPO_OWNER", "")
    REPO_NAME: str = os.getenv("REPO_NAME", "")
    BRANCH: str = os.getenv("BRANCH", "main")
    PATH_LOCAL: str = os.getenv("PATH_LOCAL", "")
   
    # Configurações das APIs
    URL_API_CLIENTE = os.getenv("URL_API_CLIENTE", "")
    URL_API_PROCESSAMENTO: str = os.getenv("URL_API_PROCESSAMENTO", "")
    PATH_MODELOS: str = os.getenv("PATH_MODELOS", "models")
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "")
    
    # Configurações do Banco de Dados
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:password@localhost:5432/Projeto")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "password")
    
settings = Settings()