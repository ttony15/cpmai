from src.exceptions.base_exception import BaseResponse


class FileUploadError(BaseResponse):
    status = "Error uploading file"


class FileProcessingError(BaseResponse):
    status = "Error processing file"


class InvalidFileTypeError(BaseResponse):
    status = "Invalid file type"


class AIServiceError(BaseResponse):
    status = "Error generating AI response"