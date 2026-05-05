"""
Cálculo de impostos sobre renda fixa conforme legislação brasileira.

IR Regressivo (Lei 11.033/2004):
    - Até 180 dias:         22,5%
    - De 181 a 360 dias:    20,0%
    - De 361 a 720 dias:    17,5%
    - Acima de 720 dias:    15,0%

IOF Regressivo (Decreto 6.306/2007):
    - Aplica-se apenas nos primeiros 29 dias.
    - Tabela diária de 96% a 0% sobre o rendimento.

LCI e LCA são isentas de IR para pessoas físicas (Lei 11.033/2004, art. 3º).
Tesouro Direto segue a mesma tabela de IR.
"""

# Tabela IOF regressiva — dia: alíquota %
_IOF_TABLE: dict[int, float] = {
    1: 96, 2: 93, 3: 90, 4: 86, 5: 83, 6: 80, 7: 76, 8: 73, 9: 70, 10: 66,
    11: 63, 12: 60, 13: 56, 14: 53, 15: 50, 16: 46, 17: 43, 18: 40, 19: 36,
    20: 33, 21: 30, 22: 26, 23: 23, 24: 20, 25: 16, 26: 13, 27: 10, 28: 6,
    29: 3, 30: 0,
}


def ir_aliquota(term_days: int) -> tuple[float, str]:
    """
    Retorna (alíquota, descrição_da_faixa) de acordo com o prazo.
    """
    if term_days <= 180:
        return 0.225, "até 180 dias — 22,5%"
    elif term_days <= 360:
        return 0.20, "de 181 a 360 dias — 20,0%"
    elif term_days <= 720:
        return 0.175, "de 361 a 720 dias — 17,5%"
    else:
        return 0.15, "acima de 720 dias — 15,0%"


def calcular_ir(rendimento_bruto: float, term_days: int) -> tuple[float, float, str]:
    """
    Calcula o IR sobre o rendimento bruto.

    Returns:
        (aliquota_pct, ir_amount, descricao_faixa)
    """
    aliquota, descricao = ir_aliquota(term_days)
    ir_amount = rendimento_bruto * aliquota
    return aliquota * 100, ir_amount, descricao


def calcular_iof(rendimento_bruto: float, term_days: int) -> float:
    """
    Calcula o IOF sobre o rendimento bruto.
    Após 30 dias, IOF = 0.
    """
    if term_days >= 30:
        return 0.0
    aliquota_pct = _IOF_TABLE.get(term_days, 0)
    return rendimento_bruto * (aliquota_pct / 100)
