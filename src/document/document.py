from typing import Optional, List, Any
from redis_om import (JsonModel, Field)
from src.common.utils import ShortUuidPk, get_db
from src.version.version import Version, CurrentVersion


class Document(JsonModel):
    editorversion: Version
    currentversion: CurrentVersion
    description: Optional[str]
    keyword: Optional[str]
    creation: int = Field(index=True, sortable=True)
    updated: int = Field(index=True, sortable=True)
    tags: Optional[str] = Field(index=True)
    category: Optional[str] = Field(index=True)
    processable: int = Field(index=True)
    privacy: str = Field(index=True, default="internal")
    state: str = Field(index=True, default="draft")
    author: str = Field(index=True)
    versions: Optional[List[Version]]

    class Meta:
        database = get_db()
        global_key_prefix = "keybase"
        model_key_prefix = "json"
        index_name = "document_idx"
        primary_key_creator_cls = ShortUuidPk
