from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_api_key
from app.database.db import get_db
from app.database import models as db_models
from app.models.simulation import CreatePositionInput, MtMResult
from app.services import mtm_service

router = APIRouter(prefix="/mtm", tags=["Marcação a Mercado"])


@router.post(
    "/positions",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar posição",
    description=(
        "Registra um título adquirido para acompanhamento via Marcação a Mercado. "
        "O face_value é o valor que o título pagará no vencimento."
    ),
)
def create_position(
    payload: CreatePositionInput,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    position = mtm_service.create_position(payload, api_key, db)
    return {"id": position.id, "alias": position.alias, "message": "Posição registrada com sucesso."}


@router.get(
    "/positions",
    summary="Listar posições abertas",
    description="Lista todos os títulos em carteira ainda não encerrados.",
)
def list_positions(
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    positions = mtm_service.list_positions(api_key, db)
    return [
        {
            "id": p.id,
            "alias": p.alias,
            "product_type": p.product_type,
            "purchase_price": p.purchase_price,
            "purchase_date": p.purchase_date.isoformat(),
            "maturity_date": p.maturity_date.isoformat(),
        }
        for p in positions
    ]


@router.get(
    "/positions/{position_id}",
    response_model=MtMResult,
    summary="Marcação a Mercado de uma posição",
    description=(
        "Calcula o preço justo do título hoje com base na taxa de mercado atual. "
        "Retorna P&L bruto e líquido, e recomendação de manter ou vender."
    ),
)
def get_mtm(
    position_id: str,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    return mtm_service.get_mtm(position_id, api_key, db)


@router.delete(
    "/positions/{position_id}",
    status_code=status.HTTP_200_OK,
    summary="Encerrar posição",
    description="Marca a posição como encerrada (título vendido ou vencido).",
)
def close_position(
    position_id: str,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    position = mtm_service.close_position(position_id, api_key, db)
    return {"id": position.id, "alias": position.alias, "message": "Posição encerrada com sucesso."}
