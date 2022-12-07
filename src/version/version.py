from typing import Optional

from redis_om import (EmbeddedJsonModel, Field)

from src.common.config import get_db


class Version(EmbeddedJsonModel):
    name: str
    content: str
    creation: int
    last: str = Field(index=True)
    owner: str

    class Meta:
        database = get_db()
        embedded = True
