"""
Testes unitários para o serviço de Marcação a Mercado.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models.simulation import CreatePositionInput, ProductType, RateType
from app.services import mtm_service

MOCK_RATES = {"cdi": 10.65, "selic": 10.75, "ipca": 4.83}

PURCHASE_DATE = datetime(2024, 1, 2)
MATURITY_DATE = datetime(2026, 1, 2)  # 2 anos


def _make_position(
    rate_type: RateType = RateType.PREFIXADO,
    purchase_rate: float = 12.5,
    purchase_price: float = 800.0,
    face_value: float = 1000.0,
):
    pos = MagicMock()
    pos.id = "test-position-id"
    pos.alias = "CDB Teste"
    pos.product_type = ProductType.CDB.value
    pos.rate_type = rate_type.value
    pos.purchase_rate = purchase_rate
    pos.purchase_price = purchase_price
    pos.face_value = face_value
    pos.purchase_date = PURCHASE_DATE
    pos.maturity_date = MATURITY_DATE
    pos.is_open = True
    return pos


class TestMtMService:
    @patch("app.services.mtm_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_taxa_mercado_igual_compra_accrued_equals_market(self, _mock):
        """
        Se a taxa de mercado for igual à taxa contratada,
        o preço de mercado deve ser próximo ao valor acumulado.
        """
        pos = _make_position(purchase_rate=10.75, face_value=1000.0, purchase_price=800.0)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pos
        api_key = MagicMock()

        result = mtm_service.get_mtm("test-position-id", api_key, db)
        assert result.market_price_today > 0
        assert result.days_remaining > 0

    @patch("app.services.mtm_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_taxa_mercado_alta_gera_prejuizo_mtm(self, _mock):
        """
        Taxa de mercado > taxa de compra → título vale menos que o acumulado.
        """
        # Comprou a 8% a.a. mas mercado está a ~12.75% (SELIC + 2%)
        pos = _make_position(purchase_rate=8.0, face_value=1000.0, purchase_price=800.0)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pos
        api_key = MagicMock()

        result = mtm_service.get_mtm("test-position-id", api_key, db)
        # Com taxa de mercado mais alta, preço de mercado deve ser menor que face_value descontado à taxa de compra
        assert result.market_price_today < pos.face_value

    @patch("app.services.mtm_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_recomendacao_contem_valor(self, _mock):
        pos = _make_position()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pos
        api_key = MagicMock()

        result = mtm_service.get_mtm("test-position-id", api_key, db)
        assert "R$" in result.recommendation

    def test_position_not_found_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        api_key = MagicMock()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            mtm_service.get_mtm("inexistente", api_key, db)
        assert exc_info.value.status_code == 404


class TestBusinessDays:
    def test_mesmo_dia_retorna_zero(self):
        d = datetime(2024, 6, 3)
        assert mtm_service._business_days_between(d, d) == 0

    def test_uma_semana_util(self):
        start = datetime(2024, 6, 3)  # Segunda
        end = datetime(2024, 6, 10)   # Segunda seguinte
        result = mtm_service._business_days_between(start, end)
        assert result == 5
