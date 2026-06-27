from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, messages_from_dict
import json
from api.schemas import ChatRequest, ChatResponse, MessageRecord, HistoryResponse
from core.agent import agent
from db.crud import get_session, save_history, delete_session
from db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):

    # Send a message to the AI Career Assistant
    session_id = request.session_id if request.session_id else str(uuid4())

    # 这边肯定要改,现在是没有一个db的查找, 但是我们再后期肯定是需要的
    # 这边是根据前端返回的内容,然后提取session-id,并且在db中查找是否存在
    db_session = await get_session(db, session_id)
    if db_session and db_session.message_json:
        # 这边我获取的是db_session的json格式,但是Langchain不支持JSON格式
        # json.loads()把json转换成python格式, messages_from_dict转换成LangChain的格式
        history = messages_from_dict(json.loads(db_session.message_json))
    else:
        history = []

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
        history.append(ai_message)
        title = history[0].content[:20]

        await save_history(db,session_id,title,history)
        return ChatResponse(response=ai_message.content, session_id=session_id)
    except Exception as e:
        history.pop()
        raise HTTPException(status_code=500, detail=str(e))


# ── 具体路由（/sessions）必须在通配符路由（/{session_id}）之前 ──────────────

# TODO: GET /sessions — 返回所有 session 列表，前端侧边栏加载用
# @router.get("/sessions")
# async def list_sessions(db: AsyncSession = Depends(get_db)):
#     ...

# TODO: DELETE /sessions — 清空所有 session，前端 "Clear all" 按钮用
# @router.delete("/sessions")
# async def clear_all_sessions(db: AsyncSession = Depends(get_db)):
#     ...

# ── 通配符路由放后面 ──────────────────────────────────────────────────────────

@router.get("/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_message = []
    if session.message_json:
        raw_message = messages_from_dict(json.loads(session.message_json))
    messages = [
        MessageRecord(
            role="human" if isinstance(message, HumanMessage) else "ai",
            content=message.content,
        )
        for message in raw_message
    ]
    return HistoryResponse(session_id=session_id, messages=messages)


@router.delete("/{session_id}")
async def clear_session(session_id: str, db: AsyncSession = Depends(get_db)):
    flag = await delete_session(session_id, db)
    if not flag:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": f"Session '{session_id}' cleared"}
