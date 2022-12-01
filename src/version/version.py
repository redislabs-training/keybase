from typing import Optional

from redis_om import (EmbeddedJsonModel, Field)


class Version(EmbeddedJsonModel):
    name: str
    content: str
    creation: int
    last: str = Field(index=True)
    owner: str

    class Meta:
        embedded = True
