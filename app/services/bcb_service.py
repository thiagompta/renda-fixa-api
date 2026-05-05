"""
Integração com a API pública do Banco Central do Brasil (BCB).
Documentação: https://dadosabertos.bcb.gov.br/
"""
import logging
from datetime import datetime, timedelta
from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)
settings = get_settings()


def _fetch_last_value(serie_id: int) -> float:
    """
    Busca o último valor disponível de uma série temporal do BCB.
    Retorna o valor como float (já em formato percentual, ex: 10.65).
    """
    url = f"{settings.BCB_API_BASE_URL}/{serie_id}/dados/ultimos/1?formato=json"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return float(data[0]["valor"])
    except httpx.HTTPError as exc:
        logger.error("Erro ao consultar BCB série %d: %s", serie_id, exc)
        raise ExternalAPIError(f"BCB API indisponível para série {serie_id}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("Resposta inesperada da BCB série %d: %s", serie_id, exc)
        raise ExternalAPIError("Formato de resposta inesperado da BCB") from exc

_FALLBACK_RATES = {"cdi": 10.65, "selic": 10.75, "ipca": 4.83}
@lru_cache(maxsize=1)
def _get_rates_cached(cache_key: str) -> dict[str, float]:
    """
    Wrapper com cache por hora — evita múltiplas chamadas à BCB na mesma hora.
    O cache_key é a hora atual (YYYY-MM-DD-HH), garantindo refresh a cada hora.
    """
    logger.info("Buscando taxas do BCB (cache_key=%s)", cache_key)
    try:
        return {
        "cdi": _fetch_last_value(settings.BCB_SERIE_CDI),
        "selic": _fetch_last_value(settings.BCB_SERIE_SELIC),
        "ipca": _fetch_last_value(settings.BCB_SERIE_IPCA_ACUM),
            }
    except ExternalAPIError:
        logger.warning("BCB indisponível — usando fallback")
        return _FALLBACK_RATES


def get_current_rates() -> dict[str, float]:
    """
    Retorna as taxas de mercado atuais.
    Cache por hora usando lru_cache com cache_key baseado no horário.
    """
    cache_key = datetime.utcnow().strftime("%Y-%m-%d-%H")
    return _get_rates_cached(cache_key)


def get_cdi_rate() -> float:
    return get_current_rates()["cdi"]


def get_selic_rate() -> float:
    return get_current_rates()["selic"]


def get_ipca_rate() -> float:
    return get_current_rates()["ipca"]
