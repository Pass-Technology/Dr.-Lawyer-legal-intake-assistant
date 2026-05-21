from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional
# No need for AsyncPostgresSaver import here if only using from state

from workflow import graph, AgentState

class StartIntakeRequest(BaseModel):
    initial_description: str

class IntakeAnswersRequest(BaseModel):
    answers: List[str]

start_intake_router = APIRouter(prefix="/api/v1", tags=["Client's side"])

# ----- Start Intake -----
@start_intake_router.post("/intake/start/{session_id}")
async def start_intake(session_id: str, request: StartIntakeRequest, req: Request):
    config = {"configurable": {"thread_id": session_id}}
    checkpointer = req.app.state.checkpointer

    try:
        initial_state = AgentState(initial_description=request.initial_description)
        
        # Use the shared checkpointer
        graph.checkpointer = checkpointer
        await graph.ainvoke(initial_state, config=config)
        
        current_state = await graph.aget_state(config)
        return current_state.values
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- Start Intake with File Upload -----
@start_intake_router.post("/intake/start/{session_id}/file")
async def start_intake_with_file(
    session_id: str,
    req: Request, # Added Request
    initial_description: str = Form(...),
    file: UploadFile = File(...)
):
    config = {"configurable": {"thread_id": session_id}}
    checkpointer = req.app.state.checkpointer

    try:
        # Process the uploaded file
        try:
            from controllers import process_uploaded_file
            extracted_text, summary = process_uploaded_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
        
        combined_description = f"{initial_description}\n\nDocument Summary:\n{summary}\n\nExtracted Text:\n{extracted_text[:500]}..."
        initial_state = AgentState(initial_description=combined_description)
        
        # FIXED: Removed 'async with' and '.from_conn_string'
        graph.checkpointer = checkpointer
        await graph.ainvoke(initial_state, config=config)
        
        current_state = await graph.aget_state(config)
        
        response_data = current_state.values
        response_data["file_summary"] = summary
        response_data["file_extracted_text_length"] = len(extracted_text)
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- Intake Answers -----
@start_intake_router.post("/intake/answers/{session_id}")
async def intake_answers(session_id: str, request: IntakeAnswersRequest, req: Request):
    config = {"configurable": {"thread_id": session_id}}
    checkpointer = req.app.state.checkpointer
    
    try:
        graph.checkpointer = checkpointer
        await graph.aupdate_state(config, {"answers": request.answers})
        result = await graph.ainvoke(None, config=config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- Get Intake State Status -----
@start_intake_router.get("/intake/{session_id}")
async def get_intake_status(session_id: str, req: Request): # Added Request
    config = {"configurable": {"thread_id": session_id}}
    checkpointer = req.app.state.checkpointer

    try:
        # FIXED: Removed 'async with'
        graph.checkpointer = checkpointer
        current_state = await graph.aget_state(config)
        return current_state.values
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        