from uuid import uuid4
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from api.schemas import ChatRequest, ChatResponse, MessageRecord, HistoryResponse
from core.agent import agent

router = APIRouter(prefix="/chat", tags=["chat"])

# 临时的 session, 在服务器重启之后就会失效
sessions: dict[str, list] = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AI Career Assistant. Omit session_id to start a new session."""
    session_id = request.session_id or str(uuid4())
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]
    history.append(HumanMessage(content=request.message))

    try:
        result = agent.invoke({"messages": history[-10:]})
        ai_message = result["messages"][-1]
        history.append(ai_message)
        return ChatResponse(response=ai_message.content, session_id=session_id)
    except Exception as e:
        history.pop()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/history", response_model=HistoryResponse)
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


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Clear the conversation history for a session."""
    sessions.pop(session_id, None)
    return {"message": f"Session '{session_id}' cleared"}
