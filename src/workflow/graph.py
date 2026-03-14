from os import getenv
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import generate_questions_node, generate_final_description_node, get_answers
from langgraph.checkpoint.postgres import PostgresSaver

# After questions (meaning after user answers are processed) → decide whether to ask more questions or finalize
def route_after_questions(state: AgentState) -> str:
    if state.error:
        return END
    if state.is_ready:
        return "generate_final"
    if state.iteration_count >= 6:  # safety
        return "generate_final"   # or END with partial
    return "generate_questions"       # loop back to generate more questions

# Routing function for directly after the generate_questions node has run
def route_from_generate_questions(state: AgentState) -> str:
    if state.error:
        return END
    # If generate_questions_node set is_ready, or max iterations reached, go to final
    if state.is_ready or state.iteration_count >= 6:
        return "generate_final"
    # Otherwise, more questions were generated, so we need answers
    return "get_answers"


# ----- PostgreSQL Checkpointer -----
DB_URL = f"postgresql://postgres.trmcjhazbucmbiekzyih:{getenv('DB_PASSWORD')}@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"


# await checkpointer.setup() # <- Run once

# ----- LangGraph Workflow Structure -----
workflow = StateGraph(state_schema=AgentState)

workflow.add_node("generate_questions", generate_questions_node)
workflow.add_node("generate_final", generate_final_description_node)
workflow.add_node("get_answers", get_answers)

# Entry
workflow.add_edge(START, "generate_questions")

# Conditional edges immediately after generate_questions
workflow.add_conditional_edges(
    "generate_questions",
    route_from_generate_questions,
    {
        "generate_final": "generate_final",
        "get_answers": "get_answers",
        END: END
    }
)

# Existing conditional edges after get_answers
workflow.add_conditional_edges(
    "get_answers",
    route_after_questions,
    {
        "generate_questions": "generate_questions",
        "generate_final": "generate_final",
        END: END
    }
)

workflow.add_edge("generate_final", END)

graph = workflow.compile(interrupt_before=["get_answers"])
