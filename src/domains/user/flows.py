from loguru import logger

import src.domains.user.schemas as user_schemas


async def persist_writer_mode(context: user_schemas.WriterModeIn):
    """
    Persis writer mode in DB
    """
    logger.info("[USER FLOW] persisting writer mode")
    logger.debug(f"[USER FLOW] {context}")

    # Rest of the logic to persist data in db using models
