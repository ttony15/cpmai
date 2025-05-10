from typing import ClassVar

from fastapi import HTTPException
from fastapi import status as sc
from pydantic import BaseModel


class BaseResponse(BaseModel):
    status: ClassVar[str]
    status_code: ClassVar[int] = sc.HTTP_400_BAD_REQUEST

    def as_exception(self):
        return HTTPException(status_code=self.status_code, detail=self.status)
