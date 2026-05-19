from fastapi import APIRouter, Body
import os
from workflow.nodes import llm
from workflow.prompts import LAWYER_OFFER_REFINEMENT_PROMPT
from pydantic import BaseModel

offer_router = APIRouter(
    prefix="/api/v1",
    tags=["Lawyer's side"],
)

# ----- Optimize offer route -----
class OfferRequest(BaseModel):
    offer: str

@offer_router.post("/optimize_offer")
async def optimize_offer(offer: OfferRequest):
    """Optimize the given offer"""

    prompt = LAWYER_OFFER_REFINEMENT_PROMPT.invoke({"lawyer_offer": offer.offer}).messages[-1].content
    response = (await llm.ainvoke(prompt))

    return response.content
