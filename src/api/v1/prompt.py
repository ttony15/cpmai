from fastapi import APIRouter

prompt_router = APIRouter(prefix="/prompt", tags=["prompt"])


@prompt_router.get(
    "/",
    operation_id="get_prompt",
    summary="Get prompt"
)
async def get_prompts():
    return {"prompts": ["prompt1", "prompt2"]}


@prompt_router.post(
    "/",
    operation_id="post_prompt",
    summary="Post prompt",
)

# ToDO: Add validation, check if it's file or not, do to Domain and them flows

# async def post_prompts():