from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from api.schemas import ChatRequest, ChatResponse, MessageRecord, HistoryResponse
from core.agent import agent
from db.crud import get_session
from db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])

# 临时的 session, 在服务器重启之后就会失效
sessions: dict[str, list] = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Send a message to the AI Career Assistant
    db_session = await get_session(db, request.session_id)
    session_id = db_session.id if db_session else str(uuid4())

    history = sessions.setdefault(session_id, [])
    history.append(HumanMessage(content=request.message))

    try:
        # 这边用一个Result的格式接收AI的AIMessage, 上传最近10条对话内容
        # result是这样格式的
        # 此时 result 的格式：
        # result = {
        #     "input": "你好",
        #     "messages": [
        #         HumanMessage(content="你好"),  # 列表第 0 个元素
        #         AIMessage(content="你也好！很高兴为你服务。", additional_kwargs={}, response_metadata={'token_usage': {'total_tokens': 20}, 'model_name': 'gpt-4o'}, id='run-12345')
        #     ]
        # }
        result = agent.invoke({"messages": history[-10:]})
        ai_message = result["messages"][-1]
        # sessions = {
        #     "session_id1": [HumanMessage(content="你好"),AIMessage(content="你也好", response_metadata={...}) ],
        #     "session_id2": [ HumanMessage(content="今天天气怎么样？"),AIMessage(content="今天晴空万里...", response_metadata={...})]
        # }
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
