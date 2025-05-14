import pymupdf
from io import BytesIO
from typing import List
from loguru import logger


async def pdf_to_txt(pdf_content: bytes) -> (str, List[str]):
    import time

    start_time = time.time()

    logger.info("Parsing PDF content asynchronously")

    pdf_bytes = BytesIO(pdf_content)
    doc = pymupdf.open(stream=pdf_bytes)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    texts = [text for text in texts if text]
    results = "".join(texts)
    duration = time.time() - start_time
    logger.info(f"PDF parsing completed in {duration:.2f} seconds")
    return results, texts
