from uuid import UUID
from pydantic import BaseModel


class BulkRowError(BaseModel):
    row: int
    field: str | None = None
    message: str


class BulkStudentsPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    will_create_classes: list[str]
    errors: list[BulkRowError]
    sample: list[dict]


class BulkStudentsApplyResponse(BaseModel):
    created_students: int
    created_classes: int
    created_student_class_links: int
    skipped_rows: int
