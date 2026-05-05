from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import ExternalAPIError, external_api_exception
from app.core.security import get_api_key
from app.database.db import get_db
from app.database import models as db_models
from app.models.simulation import (
    ProductType,
    SimulateCDBInput,
    SimulateLCILCAInput,
    SimulateTesouroDiretoInput,
    SimulationResult,
)
from app.services import cdb_service, lci_lca_service, tesouro_service

router = APIRouter(prefix="/simulate", tags=["Simulação"])


def _persist_simulation(result: SimulationResult, api_key: db_models.ApiKey, db: Session):
    """Persiste o resultado da simulação no banco para histórico."""
    record = db_models.Simulation(
        api_key_id=api_key.id,
        product_type=result.product_type.value,
        principal=result.principal,
        rate=result.rate,
        rate_type=result.rate_type.value,
        term_days=result.term_days,
        gross_amount=result.gross_amount,
        net_amount=result.net_amount,
        ir_amount=result.ir.ir_amount if result.ir else 0.0,
    )
    db.add(record)
    db.commit()


@router.post(
    "/cdb",
    response_model=SimulationResult,
    status_code=status.HTTP_200_OK,
    summary="Simular CDB",
    description=(
        "Simula um CDB nas modalidades CDI%, Prefixado ou IPCA+. "
        "Aplica IR regressivo e IOF conforme a legislação vigente."
    ),
)
def simulate_cdb(
    payload: SimulateCDBInput,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    try:
        result = cdb_service.simular_cdb(payload)
    except ExternalAPIError:
        raise external_api_exception("BCB")

    _persist_simulation(result, api_key, db)
    return result


@router.post(
    "/lci",
    response_model=SimulationResult,
    status_code=status.HTTP_200_OK,
    summary="Simular LCI",
    description="Simula uma LCI (Letra de Crédito Imobiliário). Isenta de IR para pessoa física.",
)
def simulate_lci(
    payload: SimulateLCILCAInput,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    try:
        result = lci_lca_service.simular_lci_lca(payload, ProductType.LCI)
    except ExternalAPIError:
        raise external_api_exception("BCB")

    _persist_simulation(result, api_key, db)
    return result


@router.post(
    "/lca",
    response_model=SimulationResult,
    status_code=status.HTTP_200_OK,
    summary="Simular LCA",
    description="Simula uma LCA (Letra de Crédito do Agronegócio). Isenta de IR para pessoa física.",
)
def simulate_lca(
    payload: SimulateLCILCAInput,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    try:
        result = lci_lca_service.simular_lci_lca(payload, ProductType.LCA)
    except ExternalAPIError:
        raise external_api_exception("BCB")

    _persist_simulation(result, api_key, db)
    return result


@router.post(
    "/tesouro",
    response_model=SimulationResult,
    status_code=status.HTTP_200_OK,
    summary="Simular Tesouro Direto",
    description=(
        "Simula títulos do Tesouro Direto: Tesouro Selic, Prefixado ou IPCA+. "
        "Aplica IR regressivo conforme tabela da Receita Federal."
    ),
)
def simulate_tesouro(
    payload: SimulateTesouroDiretoInput,
    api_key: db_models.ApiKey = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    try:
        result = tesouro_service.simular_tesouro(payload)
    except ExternalAPIError:
        raise external_api_exception("BCB")

    _persist_simulation(result, api_key, db)
    return result
