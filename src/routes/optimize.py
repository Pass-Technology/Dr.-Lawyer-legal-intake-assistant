from fastapi import APIRouter
from pydantic import BaseModel

from workflow.nodes import llm
from workflow.prompts import OPTIMIZE_TEXT_PROMPT

optimize_router = APIRouter(
    prefix="/api/v1",
    tags=["Utils"],
)


class OptimizeTextRequest(BaseModel):
    text: str


@optimize_router.post("/optimize")
async def optimize_text(request: OptimizeTextRequest):
    """Fix grammar and spelling and return a more professional version of the text."""

    prompt = OPTIMIZE_TEXT_PROMPT.invoke({"text": request.text}).messages[-1].content
    response = await llm.ainvoke(prompt)

    return response.content
