"""
Endpoint de comparação: ranqueia todos os produtos por rentabilidade líquida
para um mesmo prazo e valor investido.
"""
from fastapi import APIRouter, Depends

from app.core.exceptions import ExternalAPIError, external_api_exception
from app.core.security import get_api_key
from app.database import models as db_models
from app.models.simulation import (
    CompareInput, CompareItem, CompareResult,
    ProductType, RateType,
    SimulateCDBInput, SimulateLCILCAInput, SimulateTesouroDiretoInput,
)
from app.services import cdb_service, lci_lca_service, tesouro_service, bcb_service

router = APIRouter(prefix="/compare", tags=["Comparação"])

# Taxas de referência de mercado usadas na comparação
_REFERENCE_RATES = {
    ProductType.CDB:               {"rate": 110.0, "rate_type": RateType.CDI_PCT,    "desc": "CDB 110% CDI"},
    ProductType.LCI:               {"rate": 92.0,  "rate_type": RateType.CDI_PCT,    "desc": "LCI 92% CDI (isento IR)"},
    ProductType.LCA:               {"rate": 90.0,  "rate_type": RateType.CDI_PCT,    "desc": "LCA 90% CDI (isento IR)"},
    ProductType.TESOURO_SELIC:     {"rate": 0.0,   "rate_type": RateType.CDI_PCT,    "desc": "Tesouro Selic"},
    ProductType.TESOURO_PREFIXADO: {"rate": 12.5,  "rate_type": RateType.PREFIXADO,  "desc": "Tesouro Prefixado 12,5% a.a."},
    ProductType.TESOURO_IPCA:      {"rate": 6.25,  "rate_type": RateType.IPCA_PLUS,  "desc": "Tesouro IPCA+ 6,25%"},
}


@router.get(
    "",
    response_model=CompareResult,
    summary="Comparar produtos de renda fixa",
    description=(
        "Ranqueia CDB, LCI, LCA e títulos do Tesouro Direto pela rentabilidade líquida "
        "para um mesmo prazo e valor investido. Taxas de referência de mercado."
    ),
)
def compare(
    principal: float,
    term_days: int,
    api_key: db_models.ApiKey = Depends(get_api_key),
):
    try:
        rates = bcb_service.get_current_rates()
    except ExternalAPIError:
        raise external_api_exception("BCB")

    results: list[CompareItem] = []

    for product_type, ref in _REFERENCE_RATES.items():
        # LCI e LCA têm prazo mínimo — pula se não atingido
        if product_type in {ProductType.LCI, ProductType.LCA} and term_days < 90:
            continue

        try:
            match product_type:
                case ProductType.CDB:
                    sim = cdb_service.simular_cdb(
                        SimulateCDBInput(
                            principal=principal,
                            rate=ref["rate"],
                            rate_type=ref["rate_type"],
                            term_days=term_days,
                        )
                    )
                case ProductType.LCI | ProductType.LCA:
                    sim = lci_lca_service.simular_lci_lca(
                        SimulateLCILCAInput(principal=principal, rate=ref["rate"], term_days=term_days),
                        product_type,
                    )
                case _:
                    sim = tesouro_service.simular_tesouro(
                        SimulateTesouroDiretoInput(
                            product_type=product_type,
                            principal=principal,
                            rate=ref["rate"],
                            term_days=term_days,
                        )
                    )

            results.append(
                CompareItem(
                    rank=0,  # será preenchido após ordenação
                    product_type=product_type,
                    description=ref["desc"],
                    net_return_pct=sim.net_return_pct,
                    net_return_pct_aa=sim.net_return_pct_aa,
                    net_amount=sim.net_amount,
                )
            )
        except Exception:
            continue  # produto não aplicável para o prazo — ignora

    # Ordena por rentabilidade líquida anualizada (melhor primeiro)
    results.sort(key=lambda x: x.net_return_pct_aa, reverse=True)
    for i, item in enumerate(results, start=1):
        item.rank = i

    return CompareResult(
        principal=principal,
        term_days=term_days,
        cdi_rate=rates["cdi"],
        selic_rate=rates["selic"],
        ipca_rate=rates["ipca"],
        ranking=results,
    )
