from typing import Optional

from redis_om import (JsonModel, Field)
from enum import Enum

from src.common.config import get_db
from src.common.utils import ShortUuidPk


# Indexing is not yet allows by redis-om
# Error: "In this Preview release, list and tuple fields can only contain strings."
class FeedbackEnum(str, Enum):
    open = 'open'
    implemented = 'implemented'
    rejected = 'rejected'


class Feedback(JsonModel):
    document: str = Field(index=True)
    description: str
    message: str
    response: Optional[str]
    state: FeedbackEnum = Field(index=True, default=FeedbackEnum.open)
    creation: int = Field(index=True, sortable=True)
    last: Optional[int]
    reporter: str = Field(index=True)

    class Meta:
        database = get_db()
        global_key_prefix = "keybase"
        model_key_prefix = "feedback"
        index_name = "feedback_idx"
        primary_key_creator_cls = ShortUuidPk