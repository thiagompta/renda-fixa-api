"""
Serviço de simulação de LCI e LCA.

LCI (Letra de Crédito Imobiliário) e LCA (Letra de Crédito do Agronegócio)
são isentas de IR para pessoas físicas (Lei 11.033/2004).

Rendimento sempre atrelado ao CDI (% do CDI).
Prazo mínimo: 90 dias corridos (Resolução CMN 4.788/2020).
"""
from app.models.simulation import (
    ProductType, RateType, SimulateLCILCAInput, SimulationResult
)
from app.services import bcb_service


def simular_lci_lca(
    payload: SimulateLCILCAInput,
    product_type: ProductType,
) -> SimulationResult:
    rates = bcb_service.get_current_rates()
    cdi_aa = rates["cdi"] / 100

    taxa_efetiva_aa = cdi_aa * (payload.rate / 100)
    fator = (1 + taxa_efetiva_aa) ** (payload.term_days / 252)

    gross_amount = payload.principal * fator
    net_amount = gross_amount  # isento de IR

    gross_return_pct = (gross_amount / payload.principal - 1) * 100
    net_return_pct = gross_return_pct

    net_return_pct_aa = (
        ((1 + net_return_pct / 100) ** (252 / payload.term_days) - 1) * 100
        if payload.term_days > 0
        else 0.0
    )

    return SimulationResult(
        product_type=product_type,
        rate_type=RateType.CDI_PCT,
        principal=payload.principal,
        rate=payload.rate,
        term_days=payload.term_days,
        gross_amount=round(gross_amount, 2),
        gross_return_pct=round(gross_return_pct, 4),
        ir=None,  # Isento de IR
        net_amount=round(net_amount, 2),
        net_return_pct=round(net_return_pct, 4),
        net_return_pct_aa=round(net_return_pct_aa, 4),
        cdi_rate_used=rates["cdi"],
    )
