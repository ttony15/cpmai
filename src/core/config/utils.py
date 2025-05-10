from typing import Type, TypeVar

from loguru import logger
from pydantic import ValidationError
from pydantic_settings import BaseSettings

T = TypeVar("T", bound=BaseSettings)


def get_settings(setting_cls: Type[T]) -> T:
    try:
        _settings = setting_cls()  # type: ignore
        return _settings
    except ValidationError as e:
        for error in e.errors():  # noqa: B020
            error_type = error.get("type")
            location = error.get("loc")
            match error_type:
                case "missing":
                    logger.error(f"Add {''.join(location)}  ")
                case "int_parsing":
                    logger.error(f"{'.'.join(location)}  -> Wrong Value ")
                case _:
                    logger.error(error)
        raise Exception("Config Error") from e
