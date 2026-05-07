
# 后续需要改进的地方, 首先是 allow origin的部分,我们现在的策略是允许所有的地址
# 还有可以改进的地方就是 RAG 系统的streaming respons 模式

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
# from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from uuid import uuid4
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage

from chatbot.agent import agent

# App Initialization 
app = FastAPI(title="AI Job Platform", version="1.0.0")

# Allow all origins so a frontend can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> list of LangChain messages
# Each session holds its own conversation history independently
sessions: dict[str, list] = {}


# ---------- Request / Response Schemas ----------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # omit to start a new session


class ChatResponse(BaseModel):
    response: str
    session_id: str


class MessageRecord(BaseModel):
    role: str   # "human" or "ai"
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageRecord]


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chat UI."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    """Health check — confirms the server is running."""
    return {"status": "ok", "message": "AI Job Platform API is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI Career Assistant and get a response.

    - If `session_id` is omitted, a new session is created and its ID is returned.
    - Pass the same `session_id` in follow-up messages to continue the conversation.
    """
    # Create a new session if one wasn't provided
    session_id = request.session_id or str(uuid4())
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]
    history.append(HumanMessage(content=request.message))

    try:
        # Only pass the last 10 messages to avoid hitting token limits
        result = agent.invoke({"messages": history[-10:]})
        ai_message = result["messages"][-1]
        history.append(ai_message)
        return ChatResponse(response=ai_message.content, session_id=session_id)
    except Exception as e:
        # Roll back the user message so the history stays clean
        history.pop()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Return the full conversation history for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        MessageRecord(
            role="human" if isinstance(m, HumanMessage) else "ai",
            content=m.content,
        )
        for m in sessions[session_id]
    ]
    return HistoryResponse(session_id=session_id, messages=messages)


@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear the conversation history for a session."""
    sessions.pop(session_id, None)
    return {"message": f"Session '{session_id}' cleared"}
