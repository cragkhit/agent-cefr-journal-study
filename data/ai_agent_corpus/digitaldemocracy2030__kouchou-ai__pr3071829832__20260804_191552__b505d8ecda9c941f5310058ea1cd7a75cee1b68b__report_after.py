from enum import Enum

from src.schemas.base import SchemaBaseModel


class ReportStatus(Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class ReportVisibility(Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class Report(SchemaBaseModel):
    slug: str
    title: str
    description: str
    status: ReportStatus
    visibility: ReportVisibility
    is_pubcom: bool = False
    created_at: str | None = None  # 作成日時
    token_usage: int | None = None  # トークン使用量

    @property
    def is_publicly_visible(self) -> bool:
        """レポートが一般ユーザーに公開表示可能かどうかを返す"""
        return self.visibility == ReportVisibility.PUBLIC
