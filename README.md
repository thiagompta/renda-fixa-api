# Renda Fixa API

API REST para simulação, comparação e acompanhamento de investimentos em renda fixa, com suporte a **Marcação a Mercado (MtM)**.

Construída com FastAPI, SQLAlchemy e integração em tempo real com a API do Banco Central do Brasil.

---

## Funcionalidades

- **Simulação de CDB** — CDI%, Prefixado e IPCA+ com IR regressivo e IOF
- **Simulação de LCI/LCA** — isentas de IR para pessoas físicas
- **Simulação de Tesouro Direto** — Selic, Prefixado e IPCA+
- **Comparação de produtos** — ranking por rentabilidade líquida anualizada
- **Marcação a Mercado** — preço justo do título hoje, P&L e recomendação de venda
- **Taxas em tempo real** — CDI, SELIC e IPCA via BCB Open Data (cache por hora)

---

## Stack

| Componente | Tecnologia |
|---|---|
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Banco de dados | SQLite (dev) |
| Validação | Pydantic v2 |
| Autenticação | API Key (X-API-Key) |
| Dados externos | BCB Open Data API |
| Testes | pytest + pytest-cov |

---

## Instalação

```bash
git clone https://github.com/thiagompta/renda-fixa-api
cd renda-fixa-api

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
uvicorn app.main:app --reload
```

Acesse a documentação interativa em: **http://localhost:8000/docs**

---

## Autenticação

Todas as rotas (exceto `/auth` e `/rates`) exigem o header `X-API-Key`.

**1. Gere sua chave:**
```bash
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{"owner": "Seu Nome"}'
```

**2. Use nas requisições:**
```bash
curl http://localhost:8000/simulate/cdb \
  -H "X-API-Key: rf_sua-chave-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "principal": 10000,
    "rate": 110,
    "rate_type": "CDI_PCT",
    "term_days": 365
  }'
```

---

## Exemplos de uso

### Simular CDB 110% CDI por 1 ano
```json
POST /simulate/cdb
{
  "principal": 10000.00,
  "rate": 110.0,
  "rate_type": "CDI_PCT",
  "term_days": 365
}
```

### Comparar produtos para R$ 50.000 por 2 anos
```
GET /compare?principal=50000&term_days=730
```

### Registrar posição para MtM
```json
POST /mtm/positions
{
  "alias": "CDB Banco XYZ",
  "product_type": "CDB",
  "rate_type": "PREFIXADO",
  "purchase_rate": 12.5,
  "purchase_price": 10000.00,
  "face_value": 12500.00,
  "purchase_date": "2024-01-02T00:00:00",
  "maturity_date": "2026-01-02T00:00:00"
}
```

### Ver marcação a mercado
```
GET /mtm/positions/{position_id}
```

---

## Testes

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Estrutura do projeto

```
app/
├── core/          # Config, segurança, exceções
├── database/      # ORM models e sessão do banco
├── models/        # Pydantic schemas (request/response)
├── routers/       # Endpoints FastAPI
├── services/      # Lógica de negócio e cálculos financeiros
└── main.py        # Inicialização da aplicação
tests/             # Testes unitários
```

---

## Referências técnicas

- [Manual de MaM — ANBIMA](https://www.anbima.com.br/pt_br/informar/manual-de-marcacao-a-mercado.htm)
- [IR sobre renda fixa — Lei 11.033/2004](https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2004/lei/l11033.htm)
- [API do Banco Central do Brasil](https://dadosabertos.bcb.gov.br/)
- [Tesouro Direto — Preços e Taxas](https://www.tesourodireto.com.br/titulos/precos-e-taxas.htm)
