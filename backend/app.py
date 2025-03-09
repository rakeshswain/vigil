import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pathlib import Path

# Import our agent modules
from agents.web_agent import WebTestingAgent
from agents.api_agent import ApiTestingAgent

# Create FastAPI app
app = FastAPI(title="AI Testing Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
web_agent = WebTestingAgent()
api_agent = ApiTestingAgent()

# Models
class ChatRequest(BaseModel):
    message: str
    agent: str = "web"  # Default to web agent

class ChatResponse(BaseModel):
    message: str
    results: Optional[Dict[str, Any]] = None

class StatusResponse(BaseModel):
    status: str
    web_agent: bool
    api_agent: bool

# Routes
@app.get("/api/status")
async def get_status():
    """Check the status of the server and agents"""
    return StatusResponse(
        status="online",
        web_agent=web_agent.is_ready(),
        api_agent=api_agent.is_ready()
    )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Process a chat message and return a streaming response"""
    
    async def generate_response():
        try:
            # Select the appropriate agent
            agent = web_agent if request.agent == "web" else api_agent
            
            # Initial response
            yield json.dumps({
                "message": f"Processing your request with the {request.agent.capitalize()} Testing Agent..."
            }).encode() + b"\n"
            
            # Process the request with the agent
            async for response in agent.process_message(request.message):
                yield json.dumps(response).encode() + b"\n"
                
        except Exception as e:
            yield json.dumps({
                "message": f"Error: {str(e)}"
            }).encode() + b"\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="application/json"
    )

# Serve static files from the frontend directory
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

# Fallback route for SPA navigation
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    frontend_path = Path("../frontend")
    requested_path = frontend_path / full_path
    
    # If the path exists and is a file, serve it
    if requested_path.exists() and requested_path.is_file():
        return FileResponse(requested_path)
    
    # Otherwise, serve index.html for client-side routing
    return FileResponse(frontend_path / "index.html")

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the server
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
