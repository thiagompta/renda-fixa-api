from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import RendaFixaException
from app.database.db import init_db
from app.routers import auth, simulate, compare, mtm, rates

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o banco na subida da aplicação."""
    init_db()
    yield


app = FastAPI(
    title="Renda Fixa API",
    description=(
        "API para simulação de investimentos em renda fixa, comparação de produtos "
        "e Marcação a Mercado (MtM) de posições.\n\n"
        "**Autenticação:** todas as rotas (exceto `/auth` e `/rates`) exigem "
        "o header `X-API-Key`. Gere sua chave em `POST /auth/api-keys`."
    ),
    version="1.0.0",
    contact={
        "name": "Renda Fixa API",
        "url": "https://github.com/seu-usuario/renda-fixa-api",
    },
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers globais ──
@app.exception_handler(RendaFixaException)
async def renda_fixa_exception_handler(request: Request, exc: RendaFixaException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


# ── Routers ──
app.include_router(auth.router)
app.include_router(rates.router)
app.include_router(simulate.router)
app.include_router(compare.router)
app.include_router(mtm.router)


@app.get("/", include_in_schema=False)
def health_check():
    return {
        "status": "ok",
        "service": "Renda Fixa API",
        "version": "1.0.0",
        "docs": "/docs",
    }
