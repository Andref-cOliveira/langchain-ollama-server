# FastAPI server (server.py)
from fastapi import FastAPI, WebSocket
from typing import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

def get_env_or_raise(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Env var '{key}' not found")
    return value

DB_URI = get_env_or_raise("DB_URI")
connection_kwargs = {
    "autocommit": False,
    "prepare_threshold": 0,
}

llm = ChatOllama(model="deepseek-r1:14b")

async def call_model(state: MessagesState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": response}

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global lang_app
    try:
        async with AsyncConnectionPool(
            # Example configuration
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs,
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)

            # NOTE: you need to call .setup() the first time you're using your checkpointer
            await checkpointer.setup()
            
            workflow = StateGraph(state_schema=MessagesState)

            workflow.add_edge(START, "model")
            workflow.add_node("model", call_model)

            lang_app = workflow.compile(checkpointer=checkpointer)
            yield
    finally:
        print("Not Starting!")

app = FastAPI(lifespan=lifespan)

@app.websocket("/chat")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    config = {"configurable": {"thread_id": "and123"}}
        

    while True:
        user_prompt = await websocket.receive_text()
        input_messages = [HumanMessage(user_prompt)]
        response = ""
        async for chunk, metadata in lang_app.astream(
            {"messages": input_messages},
            config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessage):  # Filter to just model responses
                response += chunk.content
                await websocket.send_text(response)
    