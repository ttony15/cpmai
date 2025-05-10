from pydantic import BaseModel


class WriterModeIn(BaseModel):
    user_id: str
    tone: str
