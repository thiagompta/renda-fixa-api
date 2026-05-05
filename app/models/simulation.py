from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, model_validator


# ──────────────────────────────────────────────
# Enums de domínio
# ──────────────────────────────────────────────

class RateType(str, Enum):
    CDI_PCT = "CDI_PCT"          # % do CDI  (ex: 110% CDI)
    PREFIXADO = "PREFIXADO"      # taxa fixa  (ex: 12,50% a.a.)
    IPCA_PLUS = "IPCA_PLUS"      # IPCA + spread (ex: IPCA + 6%)


class ProductType(str, Enum):
    CDB = "CDB"
    LCI = "LCI"
    LCA = "LCA"
    TESOURO_SELIC = "TESOURO_SELIC"
    TESOURO_PREFIXADO = "TESOURO_PREFIXADO"
    TESOURO_IPCA = "TESOURO_IPCA"


# ──────────────────────────────────────────────
# Inputs de simulação
# ──────────────────────────────────────────────

class SimulateCDBInput(BaseModel):
    principal: float = Field(..., gt=0, description="Valor investido em R$")
    rate: float = Field(..., gt=0, description="Taxa contratada (ex: 110 para 110% CDI ou 12.5 para 12,5% a.a.)")
    rate_type: RateType
    term_days: int = Field(..., gt=0, le=3650, description="Prazo em dias corridos")

    model_config = {"json_schema_extra": {
        "example": {
            "principal": 10000.00,
            "rate": 110.0,
            "rate_type": "CDI_PCT",
            "term_days": 365,
        }
    }}


class SimulateLCILCAInput(BaseModel):
    principal: float = Field(..., gt=0)
    rate: float = Field(..., gt=0, description="% do CDI (ex: 92 para 92% CDI)")
    term_days: int = Field(..., gt=0, le=3650)

    @model_validator(mode="after")
    def validate_min_term(self) -> "SimulateLCILCAInput":
        # LCI/LCA têm carência mínima de 90 dias (Resolução CMN 4.788/2020)
        if self.term_days < 90:
            raise ValueError("LCI/LCA exigem prazo mínimo de 90 dias corridos.")
        return self


class SimulateTesouroDiretoInput(BaseModel):
    product_type: ProductType = Field(..., description="Tipo do título do Tesouro Direto")
    principal: float = Field(..., gt=0)
    rate: float = Field(..., gt=0, description="Taxa de compra (ex: 6.25 para IPCA+6,25%)")
    term_days: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_product_type(self) -> "SimulateTesouroDiretoInput":
        tesouro_types = {ProductType.TESOURO_SELIC, ProductType.TESOURO_PREFIXADO, ProductType.TESOURO_IPCA}
        if self.product_type not in tesouro_types:
            raise ValueError("product_type deve ser um título do Tesouro Direto.")
        return self


# ──────────────────────────────────────────────
# Output de simulação
# ──────────────────────────────────────────────

class IRBreakdown(BaseModel):
    aliquota_pct: float = Field(description="Alíquota de IR aplicada (%)")
    ir_amount: float = Field(description="Valor do IR em R$")
    bracket: str = Field(description="Faixa de IR (ex: 'até 180 dias — 22,5%')")


class SimulationResult(BaseModel):
    product_type: ProductType
    rate_type: RateType
    principal: float
    rate: float
    term_days: int
    gross_amount: float = Field(description="Montante bruto no vencimento")
    gross_return_pct: float = Field(description="Rentabilidade bruta (%)")
    ir: IRBreakdown | None = Field(description="Detalhamento do IR (None para LCI/LCA)")
    net_amount: float = Field(description="Montante líquido após IR e IOF")
    net_return_pct: float = Field(description="Rentabilidade líquida (%)")
    net_return_pct_aa: float = Field(description="Rentabilidade líquida anualizada (%)")
    cdi_rate_used: float = Field(description="Taxa CDI utilizada na simulação (%)")


# ──────────────────────────────────────────────
# Compare
# ──────────────────────────────────────────────

class CompareInput(BaseModel):
    principal: float = Field(..., gt=0)
    term_days: int = Field(..., gt=0, le=3650)


class CompareItem(BaseModel):
    rank: int
    product_type: ProductType
    description: str
    net_return_pct: float
    net_return_pct_aa: float
    net_amount: float


class CompareResult(BaseModel):
    principal: float
    term_days: int
    cdi_rate: float
    selic_rate: float
    ipca_rate: float
    ranking: list[CompareItem]


# ──────────────────────────────────────────────
# Marcação a Mercado (MtM)
# ──────────────────────────────────────────────

class CreatePositionInput(BaseModel):
    alias: str = Field(..., min_length=3, max_length=100, description="Nome amigável para identificar o título")
    product_type: ProductType
    rate_type: RateType
    purchase_rate: float = Field(..., gt=0, description="Taxa contratada na compra")
    purchase_price: float = Field(..., gt=0, description="Valor investido em R$")
    face_value: float = Field(..., gt=0, description="Valor de face no vencimento em R$")
    purchase_date: datetime
    maturity_date: datetime

    @model_validator(mode="after")
    def validate_dates(self) -> "CreatePositionInput":
        if self.maturity_date <= self.purchase_date:
            raise ValueError("maturity_date deve ser posterior a purchase_date.")
        return self


class MtMResult(BaseModel):
    position_id: str
    alias: str
    product_type: ProductType
    purchase_date: datetime
    maturity_date: datetime
    days_elapsed: int
    days_remaining: int
    purchase_price: float
    market_rate_today: float = Field(description="Taxa de mercado atual para o papel (%)")
    market_price_today: float = Field(description="Preço justo do título hoje (MtM)")
    accrued_value: float = Field(description="Valor acumulado pela taxa contratada até hoje")
    gross_pnl: float = Field(description="P&L bruto: preço mercado - preço compra")
    ir_on_sale: float = Field(description="IR estimado se vender hoje")
    net_pnl: float = Field(description="P&L líquido após IR")
    recommendation: str = Field(description="Hold ou venda — baseado no P&L líquido")
