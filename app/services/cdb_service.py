"""
Serviço de simulação de CDB.

Suporta três modalidades:
    - CDI_PCT:    rendimento atrelado a um percentual do CDI (ex: 110% CDI)
    - PREFIXADO:  taxa fixa contratada (ex: 12,5% a.a.)
    - IPCA_PLUS:  IPCA acumulado + spread prefixado (ex: IPCA + 6%)

Convenção de capitalização: juros compostos, base 252 dias úteis (padrão ANBIMA).
"""
import math

from app.models.simulation import (
    ProductType, RateType, SimulateCDBInput, SimulationResult, IRBreakdown
)
from app.services import bcb_service, tax_service


def _capitalizar(taxa_aa: float, term_days: int, base: int = 252) -> float:
    """
    Fator de capitalização composta: (1 + taxa)^(n/base).
    taxa_aa: taxa anual em decimal (ex: 0.105 para 10,5%)
    """
    return (1 + taxa_aa) ** (term_days / base)


def simular_cdb(payload: SimulateCDBInput) -> SimulationResult:
    rates = bcb_service.get_current_rates()
    cdi_aa = rates["cdi"] / 100  # converte % para decimal
    ipca_aa = rates["ipca"] / 100

    # ── Calcula a taxa efetiva anual de acordo com a modalidade ──
    match payload.rate_type:
        case RateType.CDI_PCT:
            taxa_efetiva_aa = cdi_aa * (payload.rate / 100)

        case RateType.PREFIXADO:
            taxa_efetiva_aa = payload.rate / 100

        case RateType.IPCA_PLUS:
            # IPCA + spread: capitalização composta das duas taxas
            taxa_efetiva_aa = (1 + ipca_aa) * (1 + payload.rate / 100) - 1

    fator = _capitalizar(taxa_efetiva_aa, payload.term_days)
    gross_amount = payload.principal * fator
    rendimento_bruto = gross_amount - payload.principal

    # ── IOF (primeiros 29 dias) ──
    iof = tax_service.calcular_iof(rendimento_bruto, payload.term_days)
    rendimento_apos_iof = rendimento_bruto - iof

    # ── IR Regressivo ──
    aliquota_pct, ir_amount, bracket = tax_service.calcular_ir(
        rendimento_apos_iof, payload.term_days
    )

    net_amount = payload.principal + rendimento_apos_iof - ir_amount
    gross_return_pct = (gross_amount / payload.principal - 1) * 100
    net_return_pct = (net_amount / payload.principal - 1) * 100

    # Anualiza a rentabilidade líquida
    net_return_pct_aa = (
        ((1 + net_return_pct / 100) ** (252 / payload.term_days) - 1) * 100
        if payload.term_days > 0
        else 0.0
    )

    return SimulationResult(
        product_type=ProductType.CDB,
        rate_type=payload.rate_type,
        principal=payload.principal,
        rate=payload.rate,
        term_days=payload.term_days,
        gross_amount=round(gross_amount, 2),
        gross_return_pct=round(gross_return_pct, 4),
        ir=IRBreakdown(
            aliquota_pct=aliquota_pct,
            ir_amount=round(ir_amount, 2),
            bracket=bracket,
        ),
        net_amount=round(net_amount, 2),
        net_return_pct=round(net_return_pct, 4),
        net_return_pct_aa=round(net_return_pct_aa, 4),
        cdi_rate_used=rates["cdi"],
    )
