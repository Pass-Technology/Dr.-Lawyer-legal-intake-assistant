from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from workflow import graph, DB_URL, AgentState

# Create request model
class StartIntakeRequest(BaseModel):
    initial_description: str


# Create router
start_intake_router = APIRouter(prefix="/api/v1")


# ----- Start Intake -----
@start_intake_router.post("/intake/start/{session_id}")
async def start_intake(
    session_id: str,
    request: StartIntakeRequest,
    req: Request
    ):
    """
    User provides initial case description → agent generates first questions.
    Returns questions + session state.
    """
    config = {
        "configurable": {"thread_id": session_id},
    }

    # Get the already-initialized saver from app state
    checkpointer = req.app.state.checkpointer

    try:
        # Create initial state
        initial_state = AgentState(
            initial_description=request.initial_description
        )

        # Run the workflow until it hits the interrupt point
        await checkpointer.setup()
        graph.checkpointer = checkpointer
        await graph.ainvoke(initial_state, config=config)
        
        # Get the current state after the interruption
        current_state = await graph.aget_state(config)
        return current_state.values
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Start Intake with File Upload -----
@start_intake_router.post("/intake/start/{session_id}/file")
async def start_intake_with_file(
    session_id: str,
    initial_description: str = Form(...),
    file: UploadFile = File(...)
    ):
    """
    User provides initial case description and uploads a file → 
    file is processed, summarized, and added to context → 
    agent generates first questions.
    Returns questions + session state.
    """
    config = {
        "configurable": {"thread_id": session_id},
    }

    try:
        # Process the uploaded file
        try:
            from controllers import process_uploaded_file
            extracted_text, summary = process_uploaded_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
        
        # Combine initial description with file summary
        combined_description = f"{initial_description}\n\nDocument Summary:\n{summary}\n\nExtracted Text:\n{extracted_text[:500]}..."  # Limit text length
        
        # Create initial state with combined context
        initial_state = AgentState(
            initial_description=combined_description
        )
        
        async with AsyncPostgresSaver.from_conn_string(DB_URL) as checkpointer:
            # Run the workflow until it hits the interrupt point
            graph.checkpointer = checkpointer
            await graph.ainvoke(initial_state, config=config)
            
            # Get the current state after the interruption
            current_state = await graph.aget_state(config)
            
            # Add file processing info to the response
            response_data = current_state.values
            response_data["file_summary"] = summary
            response_data["file_extracted_text_length"] = len(extracted_text)
            
            return response_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Intake Answers -----
class IntakeAnswersRequest(BaseModel):
    answers: List[str]

@start_intake_router.post("/intake/answers/{session_id}")
async def intake_answers(session_id: str, request: IntakeAnswersRequest, req: Request):
    config = {"configurable": {"thread_id": session_id}}
    
    # Get the already-initialized saver from app state
    checkpointer = req.app.state.checkpointer
    
    try:
        # Attach it to your graph
        graph.checkpointer = checkpointer
        
        # Update the state
        await graph.aupdate_state(config, {"answers": request.answers})
        
        # Invoke the graph
        result = await graph.ainvoke(None, config=config)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Get Intake State Status -----
@start_intake_router.get("/intake/{session_id}")
async def get_intake_status(session_id: str):
    """
    Get the current status of the intake process.
    """
    config = {
        "configurable": {"thread_id": session_id},
    }
    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URL) as checkpointer:
            graph.checkpointer = checkpointer
            current_state = await graph.aget_state(config)
            return current_state.values
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

