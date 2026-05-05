from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.exceptions import ExternalAPIError, external_api_exception
from app.services import bcb_service

router = APIRouter(prefix="/rates", tags=["Taxas de Mercado"])


class CurrentRatesResponse(BaseModel):
    cdi: float
    selic: float
    ipca: float
    source: str
    note: str


@router.get(
    "/current",
    response_model=CurrentRatesResponse,
    summary="Taxas de mercado atuais",
    description="Retorna CDI, SELIC e IPCA buscados em tempo real da API do Banco Central (BCB).",
)
def get_current_rates():
    try:
        rates = bcb_service.get_current_rates()
    except ExternalAPIError:
        raise external_api_exception("Banco Central do Brasil")

    return CurrentRatesResponse(
        cdi=rates["cdi"],
        selic=rates["selic"],
        ipca=rates["ipca"],
        source="Banco Central do Brasil — api.bcb.gov.br",
        note="Cache renovado a cada hora. Valores em % ao ano.",
    )
