import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.agent import app_graph
from backend.app import config
from backend.app.tools.geocoder import geocode_place
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AstroAgent API", description="Backend API for Aradhana's Daily Spiritual Companion")

# Enable CORS for React Frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request / Response Schemas
class MessagePayload(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[MessagePayload]
    birth_details: Optional[Dict[str, Any]] = None
    chart_data: Optional[Dict[str, Any]] = None
    sidereal: bool = False

class GeocodeRequest(BaseModel):
    place_name: str

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "AstroAgent"}

@app.get("/api/geocode")
def geocode_endpoint(place_name: str = Query(..., description="The place name to geocode")):
    """Resolves a place name to coordinates and timezone."""
    result = geocode_place(place_name)
    if not result:
        raise HTTPException(status_code=400, detail=f"Could not resolve place name '{place_name}'")
    return result

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams the AstroAgent's response token-by-token, alongside tool execution events
    and final state updates (computed birth chart or transit details) as Server-Sent Events (SSE).
    """
    # Map input messages to LangChain types
    langchain_messages = []
    for msg in request.messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
            
    # Set up initial LangGraph state
    # We pass the existing birth details and chart data to persist them between turns
    initial_state = {
        "messages": langchain_messages,
        "birth_details": request.birth_details,
        "chart_data": request.chart_data,
        "transits_data": None,
        "current_intent": None,
        "error": None
    }
    
    # Optional flags (e.g. passing sidereal preferences)
    # We inject it into the prompt if required, or let the tool call fetch it.
    # To support sidereal in the tools, the agent will detect it or pass it.
    
    async def sse_event_generator():
        try:
            logger.info("Starting agent event stream...")
            
            # Using version v2 of astream_events
            async for event in app_graph.astream_events(initial_state, version="v2", config={"recursion_limit": 8}):
                kind = event["event"]

                try:
                    # 1. Stream text token chunks as they are generated
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        # Guard against malformed chunks from unrecognised FinishReason enums
                        # (e.g. Gemini FinishReason 10 = MALFORMED_FUNCTION_CALL in newer API versions)
                        content = getattr(chunk, "content", None)
                        if content and isinstance(content, str):
                            payload = {"event": "token", "text": content}
                            yield f"data: {json.dumps(payload)}\n\n"
                            
                    # 2. Notify frontend of tool start execution (for glowing UI spinner)
                    elif kind == "on_tool_start":
                        name = event["name"]
                        inputs = event["data"].get("input", {})
                        label = f"Calling tool {name}..."
                        
                        if name == "geocode_place_tool":
                            label = f"Resolving spiritual coordinate boundaries for '{inputs.get('place_name', '')}'..."
                        elif name == "compute_birth_chart_tool":
                            label = "Aligning houses & calculating stellar configurations..."
                        elif name == "get_daily_transits_tool":
                            label = "Tracing current celestial currents relative to natal alignment..."
                        elif name == "knowledge_lookup_tool":
                            label = "Consulting sacred texts and astrological references..."
                            
                        payload = {"event": "tool_start", "name": name, "label": label}
                        yield f"data: {json.dumps(payload)}\n\n"
                        
                    # 3. Stream tool execution results
                    elif kind == "on_tool_end":
                        name = event["name"]
                        raw_output = event["data"].get("output", "")
                        # output may be a ToolMessage or string — serialise safely
                        if hasattr(raw_output, "content"):
                            output_str = raw_output.content
                        else:
                            output_str = str(raw_output) if raw_output is not None else ""
                        payload = {"event": "tool_end", "name": name, "output": output_str}
                        yield f"data: {json.dumps(payload)}\n\n"
                        
                    # 4. Extract final state values when the main graph chain ends
                    elif kind == "on_chain_end" and event["name"] == "LangGraph":
                        output_state = event["data"].get("output", {})
                        if output_state:
                            payload = {
                                "event": "state_update",
                                "birth_details": output_state.get("birth_details"),
                                "chart_data": output_state.get("chart_data"),
                                "transits_data": output_state.get("transits_data"),
                                "error": output_state.get("error")
                            }
                            logger.info(f"Stream complete. Yielding final state: {payload.keys()}")
                            yield f"data: {json.dumps(payload)}\n\n"

                except (AttributeError, TypeError, ValueError) as chunk_err:
                    # Skip malformed chunks (e.g. unrecognised FinishReason enum from Gemini)
                    # without aborting the entire stream
                    logger.warning(f"Skipping malformed SSE chunk ({kind}): {chunk_err}")
                    continue
                        
        except Exception as e:
            logger.error(f"Error in SSE stream generator: {str(e)}")
            error_payload = {"event": "error", "message": f"An error occurred during celestial alignment: {str(e)}"}
            yield f"data: {json.dumps(error_payload)}\n\n"
            
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

# Entry point for development run
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting AstroAgent API server on {config.HOST}:{config.PORT}")
    uvicorn.run("backend.app.main:app", host=config.HOST, port=config.PORT, reload=True)
