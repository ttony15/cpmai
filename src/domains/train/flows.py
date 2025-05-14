import asyncio
import json

from loguru import logger

import src.domains.file_processors.flows as file_processor_flows
import src.domains.train.models as train_models
import src.domains.train.schemas as train_schemas
import src.integrations.awsS3.manager as s3_manager
import src.integrations.openai.manager as openai_manager


async def train_llm(context: train_schemas.TrainIn) -> train_schemas.TrainOut:
    """
    Submit files to LLM to train
    """

    logger.info("[TRAIN FLOW] Received training request")
    logger.debug(f"[TRAIN FLOW] {context}")
    # Check if the same file is already in DB or not.
    found = await train_models.TrainFiles.find_one(
        train_models.TrainFiles.file_hash == context.file_details.file_hash,
    )

    # Generate file_key
    file_key = f"train_files/{context.file.filename}"

    # If the file is not already used to train LLM.
    if not found:
        # Upload it to S3.
        await s3_manager.upload(
            file_name=file_key,
            file_content=context.file_details.contents,
            content_type=context.file.content_type,
        )

        # Save this file in DB.
        await train_models.TrainFiles(
            file_hash=context.file_details.file_hash,
            file_key=file_key,
        ).save()

        # Parse file and submit data to train LLM
        _, extracted_text_per_page = await file_processor_flows.pdf_to_txt(
            context.file_details.contents
        )
        tasks = []
        for i, page_text in enumerate(extracted_text_per_page):
            tasks.append(create_training_prompt(page_text))
        prompts_jsonl = await asyncio.gather(*tasks)
        jsonl_training_data = "\n".join(prompts_jsonl)

        # Submit the training data to OpenAI for fine-tuning
        try:
            finetune_job = await openai_manager.finetune_model(jsonl_training_data)
            # Save finetune job id DB
            await train_models.TrainedModel(id=finetune_job.id).save()
            return train_schemas.TrainOut(
                message=f"Training job submitted successfully. Job ID: {finetune_job.id}",
                progress_url=f"https://platform.openai.com/finetune/{finetune_job.id}",
            )
        except Exception as e:
            return train_schemas.TrainOut(
                message=f"Error submitting training job: {str(e)}", progress_url=""
            )
    return train_schemas.TrainOut(
        message="Model already trained with this file",
        progress_url=None,
    )


async def create_training_prompt(page_text: str) -> str:
    """Creates a training prompt using the OpenAI manager."""
    prompt = f"Create a training prompt from this text: {page_text}"
    completion = await openai_manager.openai_complete(prompt=prompt)
    prompt_json = json.dumps({"prompt": page_text, "completion": completion})
    return prompt_json
