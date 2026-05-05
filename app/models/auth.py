from pydantic import BaseModel, Field


class CreateApiKeyInput(BaseModel):
    owner: str = Field(..., min_length=2, max_length=100, description="Nome do dono da chave")

    model_config = {"json_schema_extra": {"example": {"owner": "João Silva"}}}


class ApiKeyResponse(BaseModel):
    id: str
    owner: str
    key: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
