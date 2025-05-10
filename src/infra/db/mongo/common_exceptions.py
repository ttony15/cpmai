from typing import ClassVar

from fastapi import status as sc

from src.exceptions.base_exception import BaseResponse


class ImproperlyConfigured(BaseResponse):
    status = "fail.mongodb.improperly_configured"
    status_code: ClassVar[int] = sc.HTTP_500_INTERNAL_SERVER_ERROR
