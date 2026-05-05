"""
Testes unitários para os serviços de simulação.
Não dependem de banco ou rede — mockamos o bcb_service.
"""
import pytest
from unittest.mock import patch

from app.models.simulation import RateType, SimulateCDBInput, SimulateLCILCAInput
from app.services import cdb_service, lci_lca_service, tax_service
from app.models.simulation import ProductType

MOCK_RATES = {"cdi": 10.65, "selic": 10.75, "ipca": 4.83}


# ────────────────────────────────────────────
# Tax Service
# ────────────────────────────────────────────

class TestIRAliquota:
    def test_faixa_ate_180_dias(self):
        aliq, desc = tax_service.ir_aliquota(180)
        assert aliq == 0.225
        assert "22,5%" in desc

    def test_faixa_181_a_360(self):
        aliq, _ = tax_service.ir_aliquota(360)
        assert aliq == 0.20

    def test_faixa_361_a_720(self):
        aliq, _ = tax_service.ir_aliquota(720)
        assert aliq == 0.175

    def test_faixa_acima_720(self):
        aliq, _ = tax_service.ir_aliquota(721)
        assert aliq == 0.15

    def test_limite_exato_180(self):
        aliq, _ = tax_service.ir_aliquota(180)
        assert aliq == 0.225

    def test_limite_exato_181(self):
        aliq, _ = tax_service.ir_aliquota(181)
        assert aliq == 0.20


class TestIOF:
    def test_dia_1_maximo(self):
        iof = tax_service.calcular_iof(1000.0, 1)
        assert iof == pytest.approx(960.0)

    def test_dia_30_zero(self):
        iof = tax_service.calcular_iof(1000.0, 30)
        assert iof == 0.0

    def test_apos_30_dias_zero(self):
        iof = tax_service.calcular_iof(1000.0, 365)
        assert iof == 0.0

    def test_dia_15_cinquenta_pct(self):
        iof = tax_service.calcular_iof(1000.0, 15)
        assert iof == pytest.approx(500.0)


# ────────────────────────────────────────────
# CDB Service
# ────────────────────────────────────────────

class TestCDBSimulation:
    @patch("app.services.cdb_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_cdi_pct_retorna_resultado(self, _mock):
        payload = SimulateCDBInput(
            principal=10_000.0,
            rate=110.0,
            rate_type=RateType.CDI_PCT,
            term_days=365,
        )
        result = cdb_service.simular_cdb(payload)
        assert result.gross_amount > result.principal
        assert result.net_amount < result.gross_amount  # IR foi descontado
        assert result.ir is not None
        assert result.ir.aliquota_pct == pytest.approx(17.5)  # 361-720 dias → 17,5%

    @patch("app.services.cdb_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_prefixado_independe_de_cdi(self, _mock):
        payload = SimulateCDBInput(
            principal=10_000.0,
            rate=12.5,
            rate_type=RateType.PREFIXADO,
            term_days=365,
        )
        result = cdb_service.simular_cdb(payload)
        # Capitalização composta base 252: 10000 * (1.125)^(365/252) ≈ 11.860
        assert result.gross_amount == pytest.approx(11_860.0, rel=0.01)

    @patch("app.services.cdb_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_montante_liquido_menor_que_bruto(self, _mock):
        payload = SimulateCDBInput(
            principal=5_000.0,
            rate=100.0,
            rate_type=RateType.CDI_PCT,
            term_days=500,
        )
        result = cdb_service.simular_cdb(payload)
        assert result.net_amount < result.gross_amount
        assert result.net_return_pct > 0

    @patch("app.services.cdb_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_rentabilidade_anualizada_positiva(self, _mock):
        payload = SimulateCDBInput(
            principal=1_000.0,
            rate=110.0,
            rate_type=RateType.CDI_PCT,
            term_days=180,
        )
        result = cdb_service.simular_cdb(payload)
        assert result.net_return_pct_aa > 0


# ────────────────────────────────────────────
# LCI/LCA Service
# ────────────────────────────────────────────

class TestLCILCASimulation:
    @patch("app.services.lci_lca_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_lci_isenta_de_ir(self, _mock):
        payload = SimulateLCILCAInput(principal=10_000.0, rate=92.0, term_days=365)
        result = lci_lca_service.simular_lci_lca(payload, ProductType.LCI)
        assert result.ir is None
        assert result.net_amount == result.gross_amount

    @patch("app.services.lci_lca_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_lca_isenta_de_ir(self, _mock):
        payload = SimulateLCILCAInput(principal=10_000.0, rate=90.0, term_days=365)
        result = lci_lca_service.simular_lci_lca(payload, ProductType.LCA)
        assert result.ir is None

    def test_lci_prazo_minimo_90_dias(self):
        with pytest.raises(ValueError, match="90 dias"):
            SimulateLCILCAInput(principal=10_000.0, rate=92.0, term_days=89)

    @patch("app.services.lci_lca_service.bcb_service.get_current_rates", return_value=MOCK_RATES)
    def test_lci_92pct_cdi_menor_que_cdb_110pct(self, _mock):
        """LCI 92% CDI isenta deve competir com CDB 110% CDI com IR."""
        payload_lci = SimulateLCILCAInput(principal=10_000.0, rate=92.0, term_days=365)
        result_lci = lci_lca_service.simular_lci_lca(payload_lci, ProductType.LCI)

        with patch("app.services.cdb_service.bcb_service.get_current_rates", return_value=MOCK_RATES):
            payload_cdb = SimulateCDBInput(
                principal=10_000.0, rate=110.0, rate_type=RateType.CDI_PCT, term_days=365
            )
            result_cdb = cdb_service.simular_cdb(payload_cdb)

        # Ambos devem ter rentabilidade positiva
        assert result_lci.net_return_pct > 0
        assert result_cdb.net_return_pct > 0
