from fastapi import Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.exceptions import credentials_exception
from app.database.db import get_db
from app.database import models as db_models

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> db_models.ApiKey:
    """
    Dependency que valida o X-API-Key header.
    Injeta o objeto ApiKey nas rotas autenticadas.
    """
    if not api_key:
        raise credentials_exception()

    record = (
        db.query(db_models.ApiKey)
        .filter(db_models.ApiKey.key == api_key, db_models.ApiKey.is_active == True)
        .first()
    )

    if not record:
        raise credentials_exception()

    return record
