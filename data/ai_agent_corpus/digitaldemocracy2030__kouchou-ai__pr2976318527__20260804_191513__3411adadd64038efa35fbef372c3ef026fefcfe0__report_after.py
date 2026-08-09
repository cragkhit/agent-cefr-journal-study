from enum import Enum

from src.schemas.base import SchemaBaseModel


class ReportStatus(Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class Report(SchemaBaseModel):
    slug: str
    title: str
    description: str
    status: ReportStatus
    is_pubcom: bool = False
    is_public: bool = True  # デフォルトは公開状態
    created_at: str | None = None  # 作成日時
