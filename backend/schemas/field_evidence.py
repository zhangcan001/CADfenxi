from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FieldEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_value_id: int
    candidate_id: int
    source_type: str
    raw_text: str
    bbox: str | None
    confidence: float
    created_at: datetime
    field_name: str | None = None
