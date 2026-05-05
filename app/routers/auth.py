import secrets

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database import models as db_models
from app.models.auth import CreateApiKeyInput, ApiKeyResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gera uma nova API Key",
    description=(
        "Cria uma API Key para autenticação. "
        "Guarde a chave retornada — ela não será exibida novamente."
    ),
)
def create_api_key(payload: CreateApiKeyInput, db: Session = Depends(get_db)):
    key = f"rf_{secrets.token_urlsafe(32)}"
    record = db_models.ApiKey(owner=payload.owner, key=key)
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiKeyResponse(
        id=record.id,
        owner=record.owner,
        key=record.key,
        is_active=record.is_active,
        created_at=record.created_at.isoformat(),
    )
