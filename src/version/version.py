from redis_om import (EmbeddedJsonModel, Field)
from typing import Optional
from src.common.config import get_db

# Note. Redis OM EmbeddedJsonModel timestamps cannot have ints.
# "In this Preview release, list and tuple fields can only contain strings"

class Version(EmbeddedJsonModel):
    name: str
    content: str
    last: str = Field(index=True)
    owner: str

    class Meta:
        database = get_db()
        embedded = True

class CurrentVersion(EmbeddedJsonModel):
    name: str = Field(index=True, full_text_search=True)
    content: Optional[str] = Field(index=True, full_text_search=True)
    last: Optional[str]
    owner: Optional[str]

    class Meta:
        database = get_db()
        embedded = True