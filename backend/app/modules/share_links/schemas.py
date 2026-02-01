from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ShareLinkCreate(BaseModel):
    ai_report_id: UUID
    guardian_id: UUID | None = None

    # MVP: default 7 días, con límites razonables
    expires_in_days: int = Field(default=7, ge=1, le=30)


class ShareLinkOut(BaseModel):
    id: UUID
    ai_report_id: UUID
    guardian_id: UUID | None
    expires_at: datetime
    revoked_at: datetime | None
    url: str
