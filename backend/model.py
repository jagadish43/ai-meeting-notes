from sqlmodel import SQLModel, feild
from typing import Optional


class User(SQLModel, Table = True):
    id: Optional[int] = Field(default=None, Primary_key = True)