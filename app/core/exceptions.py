from fastapi import HTTPException, status


class RendaFixaException(Exception):
    """Base exception para o domínio da aplicação."""
    pass


class InvalidTaxaError(RendaFixaException):
    pass


class InvalidPrazoError(RendaFixaException):
    pass


class ExternalAPIError(RendaFixaException):
    pass


class ApiKeyNotFoundError(RendaFixaException):
    pass


# HTTP Exceptions prontos para uso nos routers
def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key inválida ou não encontrada.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def not_found_exception(entity: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} não encontrado.",
    )


def external_api_exception(service: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Serviço externo indisponível: {service}. Tente novamente em instantes.",
    )
