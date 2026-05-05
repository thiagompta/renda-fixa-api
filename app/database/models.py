import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Float, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    simulations: Mapped[list["Simulation"]] = relationship(back_populates="api_key")
    positions: Mapped[list["Position"]] = relationship(back_populates="api_key")


class Simulation(Base):
    """Histórico de simulações realizadas por cada chave."""
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    api_key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    product_type: Mapped[str] = mapped_column(String, nullable=False)  # CDB, LCI, LCA, TESOURO
    principal: Mapped[float] = mapped_column(Float, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    rate_type: Mapped[str] = mapped_column(String, nullable=False)  # CDI_PCT, PREFIXADO, IPCA_PLUS
    term_days: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_amount: Mapped[float] = mapped_column(Float, nullable=False)
    net_amount: Mapped[float] = mapped_column(Float, nullable=False)
    ir_amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    api_key: Mapped["ApiKey"] = relationship(back_populates="simulations")


class Position(Base):
    """
    Posição aberta de um título — usada para Marcação a Mercado.
    Representa um título que o usuário comprou e quer acompanhar.
    """
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    api_key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String, nullable=False)           # ex: "CDB Banco XYZ"
    product_type: Mapped[str] = mapped_column(String, nullable=False)
    rate_type: Mapped[str] = mapped_column(String, nullable=False)
    purchase_rate: Mapped[float] = mapped_column(Float, nullable=False)  # taxa contratada
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False) # valor investido
    face_value: Mapped[float] = mapped_column(Float, nullable=False)     # valor de face no vencimento
    purchase_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    maturity_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    api_key: Mapped["ApiKey"] = relationship(back_populates="positions")
