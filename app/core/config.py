from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite:///./renda_fixa.db"
    SECRET_KEY: str = "dev-secret-key"
    ENVIRONMENT: str = "development"
    BCB_API_BASE_URL: str = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
    ANBIMA_BASE_URL: str = "https://www.anbima.com.br/informacoes/est-termo"

    # Séries do BCB
    BCB_SERIE_CDI: int = 12          # CDI diário
    BCB_SERIE_SELIC: int = 432       # Meta SELIC
    BCB_SERIE_IPCA: int = 433        # IPCA mensal
    BCB_SERIE_IPCA_ACUM: int = 13522 # IPCA acumulado 12 meses

    # Dias úteis por ano (convenção ANBIMA)
    BUSINESS_DAYS_YEAR: int = 252


@lru_cache
def get_settings() -> Settings:
    return Settings()
