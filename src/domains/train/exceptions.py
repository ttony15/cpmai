from typing import ClassVar

from fastapi import status as sc

from src.exceptions.base_exception import BaseResponse


class InvalidFileType(BaseResponse):
    status = "fail.file_extension.invalid"
    status_code: ClassVar[int] = sc.HTTP_400_BAD_REQUEST
