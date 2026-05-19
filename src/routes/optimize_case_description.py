from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from workflow.nodes import llm
from workflow.prompts import (
    EDIT_DESCRIPTION_PROMPT,
    SIMPLE_REFINE_PROMPT,
    CaseSummaryAndTagsResult,
    case_summary_and_tags_system,
)

refine_router = APIRouter(
    prefix="/api/v1",
    tags=["Utils"],
)

_summarize_runnable = llm.with_structured_output(CaseSummaryAndTagsResult)

# ----- Optimize offer route -----
class RefineRequest(BaseModel):
    final_description: str
    comments: str

@refine_router.post("/refine_description")
async def refine_description(prompts: RefineRequest):
    """Refine the given description"""

    prompt = EDIT_DESCRIPTION_PROMPT.invoke({"final_description": prompts.final_description, "user_comment": prompts.comments}).messages[-1].content
    response = (await llm.ainvoke(prompt))

    return response.content

class SimpleRefine(BaseModel):
    description: str

@refine_router.post("/simple_refine")
async def simple_refine(description: SimpleRefine):
    """Refine the given description"""

    prompt = SIMPLE_REFINE_PROMPT.invoke({"final_description": description.description}).messages[-1].content
    response = (await llm.ainvoke(prompt))

    return response.content


class SummarizeCaseRequest(BaseModel):
    case_description: str


@refine_router.post("/summarize_case", response_model=CaseSummaryAndTagsResult)
async def summarize_case(request: SummarizeCaseRequest):
    """Return a short summary and categorization tags for a case description."""

    result = await _summarize_runnable.ainvoke([
        case_summary_and_tags_system,
        HumanMessage(content=request.case_description),
    ])
    return result
