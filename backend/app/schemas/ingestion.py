"""Schemas for upload / validation / cleaning / import endpoints."""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    sheets: list[str] | None = None


class PreviewRequest(BaseModel):
    sheet: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ValidateRequest(BaseModel):
    sheet: str | None = None
    mapping: dict[str, str]


class CleanRequest(BaseModel):
    job_id: str


class ConfirmRequest(BaseModel):
    job_id: str


class JobOut(BaseModel):
    id: str
    file_id: str
    sheet_name: str | None = None
    status: str
    stats: dict | None = None
    error: str | None = None

    model_config = {"from_attributes": True}
