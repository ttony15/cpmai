from fastapi import APIRouter, UploadFile, File, Form

import src.domains.train.schemas as train_schemas
import src.domains.train.flows as train_flows

training_router = APIRouter(tags=["Train"])


@training_router.post(
    "/upload",
    operation_id="api.training.upload",
    summary="Endpoint to upload file for training",
)
async def train(
    file: UploadFile = File(...),
    file_type: train_schemas.TrainFileOptions = Form(...),
    domain: train_schemas.TrainFileDomain = Form(...),
) -> train_schemas.TrainOut:
    """
    Endpoint to train llm with given files
    """
    train_in = train_schemas.TrainIn(
        file=file,
        file_type=file_type,
        domain=domain,
    )
    file_details = train_schemas.FileDetails(file=file)
    train_in.file_details = file_details
    train_out = await train_flows.train_llm(train_in)
    return train_out
