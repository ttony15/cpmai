"""
OpenAI Manager for Process Project Files Lambda
-------------------------------------------------------------
This file contains functions for interacting with OpenAI for the process_project_files_lambda.
"""

import os

import openai
from loguru import logger

# Assuming settings are imported from a central location
# If not, you may need to define API key and other settings here

OPEN_API_KEY = os.environ.get("OPEN_API_KEY")


def send_to_openai(file_content, file_name, document_category):
    """
    Send file content to OpenAI for processing

    Args:
        file_content (bytes or str): The content of the file as bytes (for PDFs) or string
        file_name (str): The name of the file
        document_category (str): The category of the document

    Returns:
        dict: The response from OpenAI, or None if an error occurs
    """
    try:
        logger.info(
            f"Sending file to OpenAI: {file_name}, Category: {document_category}"
        )

        # Initialize OpenAI client
        client = openai.OpenAI(api_key=OPEN_API_KEY)

        # Check if the file is a PDF
        is_pdf = file_name.lower().endswith(".pdf")

        if is_pdf:
            # For PDF files, use the file upload API
            from io import BytesIO

            logger.info(f"Processing PDF file: {file_name}")

            # Create a BytesIO object from the file content
            file_bytes = BytesIO(file_content)

            # Create a prompt that includes file metadata
            prompt = (
                f"""
            Process the following PDF file:
            Filename: {file_name}
            Category: {document_category}

            Please analyze this file and provide insights based on its content and category.
            
            respond back with JSON 
            JSON example:
            """
                + """
            {
            "potential_errors": ["Give list of potential errors or any contradictory information in the file"],
            "questions": ["Give the list of questions if you have any for further investigations"],
            "trade_requirements": ["Give all list of trade requirements based on this document"],
            }
            """
            )

            # Send it to OpenAI with the file
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that processes and analyzes files. You will analyze the provided PDF document.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:application/pdf;base64,{file_bytes}"
                                },
                            },
                        ],
                    },
                ],
                temperature=0.7,
            )
        else:
            # For text files, decode the bytes to string if needed
            if isinstance(file_content, bytes):
                try:
                    file_content = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    logger.error(f"Failed to decode file content as UTF-8: {file_name}")
                    return None

            # Create a prompt that includes file metadata
            prompt = f"""
            Process the following file:
            Filename: {file_name}
            Category: {document_category}

            File Content:
            {file_content}

            Please analyze this file and provide insights based on its content and category.
            """

            # Send it to OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that processes and analyzes files.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

        logger.info(f"Successfully processed file with OpenAI: {file_name}")

        # Return the response
        return {
            "file_name": file_name,
            "document_category": document_category,
            "analysis": response.choices[0].message.content,
        }
    except Exception as e:
        logger.error(f"Error sending file to OpenAI: {e}")
        return None
