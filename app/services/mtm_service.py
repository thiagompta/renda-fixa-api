"""
Serviço de Marcação a Mercado (MtM — Mark to Market).

Conceito:
    Um título de renda fixa prefixado tem seu preço justo determinado pelo
    valor presente dos fluxos futuros descontados pela taxa de mercado atual.

    Se a taxa de mercado SUBIU desde a compra  → preço de mercado cai (prejuízo MtM)
    Se a taxa de mercado CAIU desde a compra   → preço de mercado sobe (ganho MtM)

Fórmula (títulos prefixados e IPCA+):
    PU_mercado = Valor_de_Face / (1 + taxa_mercado) ^ (dias_úteis_restantes / 252)

Referência: Manual de Marcação a Mercado ANBIMA.
"""
from datetime import datetime, date

from sqlalchemy.orm import Session

from app.core.exceptions import not_found_exception
from app.database import models as db_models
from app.models.simulation import (
    CreatePositionInput, MtMResult, ProductType, RateType
)
from app.services import bcb_service, tax_service


def _business_days_between(start: datetime, end: datetime) -> int:
    """
    Aproximação de dias úteis entre duas datas.
    Para produção real, usar pandas.bdate_range ou calendário ANBIMA.
    """
    delta = (end.date() - start.date()).days
    weeks = delta // 7
    remainder = delta % 7
    # Aproximação: ~5/7 dos dias são úteis
    return weeks * 5 + min(remainder, 5)


def _market_rate_for_product(product_type: ProductType, rate_type: RateType) -> float:
    """
    Retorna a taxa de mercado atual para descontar o título.
    Em produção, viria da curva ETTJ da ANBIMA por vértice de prazo.
    Aqui usamos as taxas do BCB como proxy.
    """
    rates = bcb_service.get_current_rates()

    match rate_type:
        case RateType.CDI_PCT:
            return rates["cdi"] / 100
        case RateType.PREFIXADO:
            # Proxy: usamos SELIC + spread de 2% (representa risco bancário)
            return (rates["selic"] + 2.0) / 100
        case RateType.IPCA_PLUS:
            return (rates["ipca"] + 6.0) / 100  # spread médio de mercado
        case _:
            return rates["selic"] / 100


def create_position(
    payload: CreatePositionInput,
    api_key: db_models.ApiKey,
    db: Session,
) -> db_models.Position:
    position = db_models.Position(
        api_key_id=api_key.id,
        alias=payload.alias,
        product_type=payload.product_type.value,
        rate_type=payload.rate_type.value,
        purchase_rate=payload.purchase_rate,
        purchase_price=payload.purchase_price,
        face_value=payload.face_value,
        purchase_date=payload.purchase_date,
        maturity_date=payload.maturity_date,
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def get_mtm(
    position_id: str,
    api_key: db_models.ApiKey,
    db: Session,
) -> MtMResult:
    position = (
        db.query(db_models.Position)
        .filter(
            db_models.Position.id == position_id,
            db_models.Position.api_key_id == api_key.id,
            db_models.Position.is_open == True,
        )
        .first()
    )

    if not position:
        raise not_found_exception("Posição")

    now = datetime.utcnow()
    product_type = ProductType(position.product_type)
    rate_type = RateType(position.rate_type)

    days_elapsed = _business_days_between(position.purchase_date, now)
    days_remaining = _business_days_between(now, position.maturity_date)
    days_remaining = max(days_remaining, 1)  # evita divisão por zero

    # ── Valor acumulado pela taxa contratada até hoje ──
    fator_acumulado = (1 + position.purchase_rate / 100) ** (days_elapsed / 252)
    accrued_value = position.purchase_price * fator_acumulado

    # ── Preço de mercado (MtM) ──
    taxa_mercado = _market_rate_for_product(product_type, rate_type)
    market_price = position.face_value / ((1 + taxa_mercado) ** (days_remaining / 252))

    # ── P&L ──
    gross_pnl = market_price - position.purchase_price

    # IR sobre o ganho se vender hoje
    _, ir_on_sale, _ = tax_service.calcular_ir(
        max(gross_pnl, 0), days_elapsed
    )
    net_pnl = gross_pnl - ir_on_sale

    # ── Recomendação simples ──
    if net_pnl >= 0:
        recommendation = (
            f"✅ Venda antecipada gera ganho líquido de R$ {net_pnl:,.2f}. "
            "Avalie se o reinvestimento compensa."
        )
    else:
        recommendation = (
            f"⚠️ Venda antecipada gera prejuízo líquido de R$ {abs(net_pnl):,.2f}. "
            "Recomenda-se manter até o vencimento."
        )

    return MtMResult(
        position_id=position.id,
        alias=position.alias,
        product_type=product_type,
        purchase_date=position.purchase_date,
        maturity_date=position.maturity_date,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        purchase_price=round(position.purchase_price, 2),
        market_rate_today=round(taxa_mercado * 100, 4),
        market_price_today=round(market_price, 2),
        accrued_value=round(accrued_value, 2),
        gross_pnl=round(gross_pnl, 2),
        ir_on_sale=round(ir_on_sale, 2),
        net_pnl=round(net_pnl, 2),
        recommendation=recommendation,
    )


def list_positions(api_key: db_models.ApiKey, db: Session) -> list[db_models.Position]:
    return (
        db.query(db_models.Position)
        .filter(
            db_models.Position.api_key_id == api_key.id,
            db_models.Position.is_open == True,
        )
        .order_by(db_models.Position.maturity_date)
        .all()
    )


def close_position(
    position_id: str,
    api_key: db_models.ApiKey,
    db: Session,
) -> db_models.Position:
    position = (
        db.query(db_models.Position)
        .filter(
            db_models.Position.id == position_id,
            db_models.Position.api_key_id == api_key.id,
        )
        .first()
    )

    if not position:
        raise not_found_exception("Posição")

    position.is_open = False
    position.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(position)
    return position
