import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

from orchestrator import YouTubeOrchestrator
from storage_v2 import Storage
from api_models import VideoProcessRequest, VideoProcessResponse, ReconstructionRequest, TransferRequest

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

# Init FastAPI
app = FastAPI(title="YouTube Learning Orchestrator API")

# CORS Setup
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://lovable.dev",
    "https://youtubelearningorchestrator.lovable.app",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing!")

supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Supabase JWT token.
    Returns the user object if valid, raises 401 otherwise.
    """
    token = credentials.credentials
    try:
        # Verify token with Supabase Auth
        # data = supabase_admin.auth.get_user(token) # Check if this is the right way for admin to verify user token
        # Actually client libraries usually handle this by passing the token in the header to a new client instance
        
        # We need a client that acts as the user
        client = create_client(SUPABASE_URL, SUPABASE_KEY, options={'headers': {'Authorization': f'Bearer {token}'}})
        user = client.auth.get_user()
        
        if not user or not user.user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user.user
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_orchestrator(user = Depends(get_current_user)):
    # Initialize Orchestrator with a user-specific storage instance
    # We need to recreate the client with the user's token so RLS works
    # However, in get_current_user we already created a client. 
    # Let's optimize: pass the token or client?
    # get_current_user returns User object.
    
    # We need to access the token again to create the client for storage
    # FastAPI doesn't easily let us get the token *value* from the user object dependency unless we return it too.
    # Let's adjust get_current_user logic or just re-extract from request?
    pass

# Adjusted dependency to return both user and authenticated client
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "YouTube Learning Orchestrator API",
        "docs": "/docs"
    }

def get_auth_context(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Create client representing the user
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.auth.set_session(access_token=token, refresh_token=token) # refresh_token might not be needed if we don't refresh
        # Alternatively, just set headers
        client.postgrest.headers.update({'Authorization': f'Bearer {token}'}) # This is often how supabase-py works for RLS
        
        # Verify via get_user
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
             raise HTTPException(status_code=401, detail="Invalid token")
             
        return {"user": user_response.user, "client": client}
    except Exception as e:
        logger.error(f"Auth context error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/videos/process", response_model=VideoProcessResponse)
async def process_videos(request: VideoProcessRequest, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    orchestrator = YouTubeOrchestrator(user_id, storage)
    
    result = await orchestrator.register_videos(request.urls)
    return result

@app.get("/api/roadmap")
async def get_roadmap(context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    
    roadmap = storage.get_roadmap()
    if not roadmap:
        return {"sequence": []}
    return roadmap

@app.get("/api/modules/{module_id}")
async def get_module(module_id: str, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    
    module = storage.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module

@app.post("/api/sessions")
async def create_session(module_id: str = Header(..., alias="X-Module-Id"), context: dict = Depends(get_auth_context)):
    # Note: Header approach is one way, or body. The frontend hooks might expect params.
    # checking hooks: useCreateSession() usually takes module_id.
    # Let's support body for better practice
    pass

# Refactoring create_session to take body usually preferred, but let's check what hooks expect.
# "useCreateSession()" implies it interacts with an endpoint.
# I'll support a simple body {"module_id": "..."}
class CreateSessionRequest(BaseModel):
    module_id: str

@app.post("/api/sessions")
async def create_session_endpoint(request: CreateSessionRequest, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    
    session_id = storage.create_session(request.module_id)
    if not session_id:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return {"session_id": session_id}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.post("/api/sessions/{session_id}/reconstruction")
async def submit_reconstruction(session_id: str, request: ReconstructionRequest, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    orchestrator = YouTubeOrchestrator(user_id, storage)
    
    result = await orchestrator.handle_reconstruction(session_id, request.explanation)
    return result

@app.get("/api/sessions/{session_id}/attack")
async def get_attack(session_id: str, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    orchestrator = YouTubeOrchestrator(user_id, storage)
    
    result = await orchestrator.get_attack_question(session_id)
    return result

@app.post("/api/sessions/{session_id}/repair")
async def submit_repair(session_id: str, request: ReconstructionRequest, context: dict = Depends(get_auth_context)):
    # Repair is just another reconstruction attempt (Step 4)
    return await submit_reconstruction(session_id, request, context)

@app.post("/api/sessions/{session_id}/transfer")
async def submit_transfer(session_id: str, request: TransferRequest, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    orchestrator = YouTubeOrchestrator(user_id, storage)
    
    result = await orchestrator.handle_transfer(session_id, request.attempt)
    return result

@app.post("/api/sessions/{session_id}/complete")
async def complete_session(session_id: str, context: dict = Depends(get_auth_context)):
    user_id = context['user'].id
    client = context['client']
    storage = Storage(user_id=user_id, client=client)
    orchestrator = YouTubeOrchestrator(user_id, storage)
    
    result = await orchestrator.complete_session(session_id)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
