"""
Serviço de simulação de títulos do Tesouro Direto.

Tesouro Selic:     rendimento atrelado à SELIC (SELIC + spread, geralmente 0%)
Tesouro Prefixado: taxa fixa definida na compra
Tesouro IPCA+:     IPCA acumulado + spread prefixado

IR: mesma tabela regressiva do CDB (não isento).
"""
from app.models.simulation import (
    ProductType, RateType, SimulateTesouroDiretoInput, SimulationResult, IRBreakdown
)
from app.services import bcb_service, tax_service


def simular_tesouro(payload: SimulateTesouroDiretoInput) -> SimulationResult:
    rates = bcb_service.get_current_rates()
    selic_aa = rates["selic"] / 100
    ipca_aa = rates["ipca"] / 100

    match payload.product_type:
        case ProductType.TESOURO_SELIC:
            # Tesouro Selic rende SELIC + pequeno spread (aqui usamos a taxa fornecida como spread)
            taxa_efetiva_aa = selic_aa + (payload.rate / 100)
            rate_type = RateType.CDI_PCT  # aproximação para display

        case ProductType.TESOURO_PREFIXADO:
            taxa_efetiva_aa = payload.rate / 100
            rate_type = RateType.PREFIXADO

        case ProductType.TESOURO_IPCA:
            taxa_efetiva_aa = (1 + ipca_aa) * (1 + payload.rate / 100) - 1
            rate_type = RateType.IPCA_PLUS

        case _:
            raise ValueError(f"product_type inválido: {payload.product_type}")

    fator = (1 + taxa_efetiva_aa) ** (payload.term_days / 252)
    gross_amount = payload.principal * fator
    rendimento_bruto = gross_amount - payload.principal

    iof = tax_service.calcular_iof(rendimento_bruto, payload.term_days)
    rendimento_apos_iof = rendimento_bruto - iof

    aliquota_pct, ir_amount, bracket = tax_service.calcular_ir(
        rendimento_apos_iof, payload.term_days
    )

    net_amount = payload.principal + rendimento_apos_iof - ir_amount
    gross_return_pct = (gross_amount / payload.principal - 1) * 100
    net_return_pct = (net_amount / payload.principal - 1) * 100
    net_return_pct_aa = (
        ((1 + net_return_pct / 100) ** (252 / payload.term_days) - 1) * 100
        if payload.term_days > 0
        else 0.0
    )

    return SimulationResult(
        product_type=payload.product_type,
        rate_type=rate_type,
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
