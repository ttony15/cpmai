import src.domains.train.schemas as train_schemas
import src.domains.train.models as train_models
import src.integrations.awsS3.manager as s3_manager


async def train_llm(context: train_schemas.TrainIn) -> train_schemas.TrainOut:
    """
    Submit files to LLM to train
    """
    # Check if the same file is already in DB or not.
    for file_details, file in zip(context.files_details, context.files):
        found = await train_models.TrainFiles.find_one(
            train_models.TrainFiles.file_hash == file_details.hash,
        )
        # If the file is not already used to train LLM.
        if not found:
            # Upload it to S3.
            file_key = f"train_files/{file.filename}"
            await s3_manager.upload(
                file_name=file_key,
                file_content=file_details.contents,
                content_type=file.content_type,
            )

            # Save this file in DB.
            await train_models.TrainFiles(
                file_hash=file_details.hash,
                file_key=file_key,
            ).save()

        # Submit this file to LLM to train
